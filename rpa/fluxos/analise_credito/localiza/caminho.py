"""
Localiza Meoo Revendas · Criação de lead + leitura de pré-análise.

Portal: https://localiza.my.site.com/meoorevendas/s/  (Salesforce Experience Cloud)

Fluxo:
1. Nova aba → navega para o portal (cookies da sessão persistente já estão lá)
2. Clica em Criar
3. Tela 1: preenche CPF formatado (xxx.xxx.xxx-xx) → Avançar
4. Tela 2: preenche nome, celular, email, telefone, email_revenda, descrição → Avançar
5. Aguarda "Lead criado com sucesso!" → clica "Ir para o lead"
6. Polling reload até "Status da Pré-análise de Crédito" = Concluída (~10-15s)
7. Lê "Resultado Pré-análise" → Aprovado / Reprovado

Obs:
- CPF obrigatoriamente formatado com pontos/traço.
- Dados fixos de contato (celular, email etc.) definidos neste arquivo.
- Se sessão expirar, o fluxo lança exceção (login manual necessário).
"""

import re

from ....modelos import (
    Cliente,
    ResultadoCredito,
    STATUS_APROVADO,
    STATUS_REPROVADO,
    STATUS_PENDENTE,
    STATUS_ERRO,
)
from ....util import so_digitos

PORTAL = "https://localiza.my.site.com/meoorevendas/s/"

_CELULAR         = "(11)98888-7777"
_EMAIL_PROSPECT  = "xxx@gmail.com"
_TELEFONE        = "(99)9999-9999"
_EMAIL_REVENDA   = "priscila.oliveira@inovareseguros.com"
_DESCRICAO       = "xxx"


def _formatar_doc(doc: str) -> str:
    d = so_digitos(doc)
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def _mapear(texto: str) -> str:
    t = texto.lower()
    if "aprovado" in t:
        return STATUS_APROVADO
    if "reprovado" in t or "recusado" in t or "negado" in t or "fora do perfil" in t:
        return STATUS_REPROVADO
    return STATUS_PENDENTE


def _fill(page, label: str, valor: str) -> bool:
    try:
        page.get_by_label(label, exact=False).first.fill(valor, timeout=4000)
        return True
    except Exception:
        return False


def _clicar_criar(page) -> None:
    tentativas = [
        lambda: page.get_by_role("button", name="Criar").click(timeout=8000),
        lambda: page.locator("button:has-text('Criar')").first.click(timeout=5000),
        lambda: page.get_by_text("Criar", exact=True).first.click(timeout=5000),
        lambda: page.locator("a:has-text('Criar')").first.click(timeout=5000),
    ]
    for fn in tentativas:
        try:
            fn()
            return
        except Exception:
            continue
    raise Exception("Botão 'Criar' não encontrado no portal Localiza")


def _fill_cpf(page, cpf_fmt: str) -> None:
    """
    Preenche o campo 'Digite o CPF/CNPJ' que já fica visível na página inicial.
    O formulário 'Cadastro de Lead' está sempre presente — sem necessidade de clicar Criar.
    """
    # Aguarda o form aparecer
    page.wait_for_selector("text=Cadastro de Lead", timeout=15000)
    page.wait_for_timeout(1000)

    # Tenta pelo label exato que aparece na tela
    for label in ["Digite o CPF/CNPJ", "CPF/CNPJ", "CPF", "CNPJ"]:
        try:
            loc = page.get_by_label(label, exact=False).first
            if loc.count() > 0 and loc.is_visible(timeout=2000):
                loc.fill(cpf_fmt, timeout=6000)
                print(f"   Localiza: CPF preenchido via label {label!r}")
                return
        except Exception:
            continue

    # Tenta pelo input dentro do form Cadastro de Lead
    for sel in [
        "input[placeholder*='CPF']",
        "input[placeholder*='CNPJ']",
        "input[placeholder*='cpf' i]",
        "input[placeholder*='cnpj' i]",
        "input[placeholder*='Digite']",
    ]:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=2000):
                loc.fill(cpf_fmt, timeout=6000)
                print(f"   Localiza: CPF preenchido via placeholder {sel!r}")
                return
        except Exception:
            continue

    raise Exception("Campo CPF/CNPJ não encontrado no formulário 'Cadastro de Lead'")


def _extrair(texto: str, campo: str) -> str:
    m = re.search(rf'{re.escape(campo)}\s+([^\n]+)', texto)
    return m.group(1).strip() if m else ""


def _ler_resultado(page) -> str:
    """
    Lê o resultado de pré-aprovação da página aberta.
    Suporta Lead ('Resultado Pré-análise') e Conta ('Cliente pré-aprovado?').
    """
    texto = page.evaluate("() => document.body.innerText") or ""
    return (
        _extrair(texto, "Resultado Pré-análise")       # Lead (CPF)
        or _extrair(texto, "Cliente pré-aprovado?")    # Conta (CNPJ)
        or _extrair(texto, "Cliente pré-aprovado")     # variação sem '?'
    )


class Localiza:
    nome = "localiza"
    automatico = True

    def consultar(self, cliente: Cliente, context, *, enviar: bool = False) -> ResultadoCredito:
        cpf_fmt = _formatar_doc(cliente.documento)
        cpf_dig = so_digitos(cliente.documento)
        page = context.new_page()

        try:
            page.goto(PORTAL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            # O form "Cadastro de Lead" já está na página — não clicar em Criar
            # Tela 1: CPF
            _fill_cpf(page, cpf_fmt)
            page.wait_for_timeout(500)
            page.get_by_role("button", name="Avançar").click(timeout=10000)
            page.wait_for_timeout(2500)

            # Tela 2: dados do lead
            if not _fill(page, "Nome / Razão Social", cliente.nome):
                _fill(page, "Nome", cliente.nome)
            _fill(page, "Celular",           _CELULAR)
            _fill(page, "Email do prospect", _EMAIL_PROSPECT)
            _fill(page, "Telefone",          _TELEFONE)
            _fill(page, "Email da revenda",  _EMAIL_REVENDA)
            _fill(page, "Descrição",         _DESCRICAO)

            page.wait_for_timeout(500)
            page.get_by_role("button", name="Avançar").click(timeout=10000)

            # Aguarda banner de sucesso (Lead ou Conta criado)
            page.wait_for_selector("text=criado com sucesso", timeout=30000)

            # Navega para o registro
            page.get_by_text("Ir para o lead", exact=False).click(timeout=10000)
            page.wait_for_url(
                lambda u: "/lead/" in u.lower() or "/conta/" in u.lower()
                          or "/account/" in u.lower(),
                timeout=30000,
            )

            # Aguarda Salesforce processar a pré-análise (~10s)
            page.wait_for_timeout(10000)

            resultado_raw = _ler_resultado(page)

            # Se ainda vazio (análise ainda processando), tenta mais uma vez
            if not resultado_raw:
                page.wait_for_timeout(10000)
                resultado_raw = _ler_resultado(page)

            return ResultadoCredito(
                status=_mapear(resultado_raw),
                locadora="localiza",
                documento=cpf_dig,
                detalhe=resultado_raw or "resultado não encontrado",
            )

        except Exception as exc:
            return ResultadoCredito(
                status=STATUS_ERRO,
                locadora="localiza",
                documento=cpf_dig,
                detalhe=str(exc),
            )
        finally:
            page.close()
