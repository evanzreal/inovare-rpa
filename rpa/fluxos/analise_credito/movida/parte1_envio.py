"""
Movida · Análise de crédito · PARTE 1 — ENVIO DO LEAD.  [✅ FEITO]

Preenche e envia a LP "Carro por Assinatura", o que DISPARA a analise de credito
na Movida. O veredito (aprovado/reprovado) NAO aparece aqui — ele cai no portal
logado do vendedor e e lido na PARTE 2 (parte2_resultado.py).

Mapa da pagina:
  inputs:        #name, #cpf, #phone, #email
  modelo carro:  combobox custom #lp-cpa-vehicle-trigger -> filtro .lp-cpa-vehicle-filter
                 -> lista por API .lp-cpa-vehicle-option (selecao injeta pdmVersionId/fipe)
  regiao:        <select #lp-cpa-region-select>
  radios:        motorista de app #lp-cpa-driver-yes/no ; contrato estendido
                 #lp-cpa-extended-contract-yes/no
  cod. vendedor: link .clickVendedor revela #VendedorID
  enviar:        #btnSend  ->  reCAPTCHA Enterprise (invisivel/score) + POST /api/v5/lead
"""

from dataclasses import dataclass, field

from playwright.sync_api import TimeoutError as PWTimeout

from . import config
from ..regioes import regiao_por_ddd
from ....navegador import RAIZ
from ....util import so_digitos

SAIDAS = RAIZ / "saidas" / "credito" / "movida"


@dataclass
class ResultadoEnvio:
    ok: bool
    cpf: str
    status_http: int | None = None
    resposta: str = ""
    carro_escolhido: str = ""
    regiao: str = ""
    erro: str = ""
    print_path: str = ""


def _fechar_cookies(page):
    for sel in [
        "button:has-text('Aceitar')", "button:has-text('aceitar')",
        "button:has-text('Concordo')", "#onetrust-accept-btn-handler",
        "button:has-text('Entendi')",
    ]:
        try:
            b = page.locator(sel).first
            if b.is_visible(timeout=1000):
                b.click(timeout=2000)
                page.wait_for_timeout(300)
                return
        except Exception:
            pass


def _escolher_carro(page, filtro: str) -> str:
    page.locator("#lp-cpa-vehicle-trigger").click()
    page.wait_for_timeout(500)
    busca = page.locator(".lp-cpa-vehicle-filter")
    palavra = filtro.split()[0]
    busca.fill(palavra)
    page.wait_for_selector(".lp-cpa-vehicle-option", timeout=15000)
    page.wait_for_timeout(800)

    opcoes = page.locator(".lp-cpa-vehicle-option")
    n = opcoes.count()
    textos = [opcoes.nth(i).inner_text().strip() for i in range(n)]

    alvo_idx, alvo_txt = None, ""
    termos = [t.lower() for t in filtro.split()]
    for i, t in enumerate(textos):
        if all(termo in t.lower() for termo in termos):
            alvo_idx, alvo_txt = i, t
            break
    if alvo_idx is None:
        for i, t in enumerate(textos):
            if termos[-1] in t.lower():
                alvo_idx, alvo_txt = i, t
                break
    if alvo_idx is None and n > 0:
        alvo_idx, alvo_txt = 0, textos[0]
    if alvo_idx is None:
        raise RuntimeError(f"Nenhuma opcao de carro para '{filtro}'. Opcoes: {textos}")

    print(f"   carros encontrados ({n}): {textos[:8]}{'...' if n > 8 else ''}")
    print(f"   -> selecionando: '{alvo_txt}'")
    opcoes.nth(alvo_idx).click()
    page.wait_for_timeout(400)
    return alvo_txt


def _marcar_radio(page, id_radio: str):
    try:
        page.locator(f"#{id_radio}").check(force=True, timeout=3000)
    except Exception:
        page.locator(f"label[for='{id_radio}']").click(timeout=3000)


def enviar_lead(
    nome: str,
    cpf: str,
    *,
    regiao: str | None = None,
    telefone: str = config.TELEFONE,
    email: str = config.EMAIL,
    cod_vendedor: str = config.COD_VENDEDOR,
    carro: str = config.CARRO,
    driver_app: str = config.DRIVER_APP,
    contrato_estendido: str = config.CONTRATO_ESTENDIDO,
    context=None,
    salvar_print: bool = True,
    enviar: bool = True,
) -> ResultadoEnvio:
    """Preenche e envia o lead na LP da Movida usando um 'context' ja aberto."""
    if context is None:
        raise ValueError("Passe um 'context' do Playwright (rpa.navegador.abrir_navegador).")

    if not regiao:
        regiao = regiao_por_ddd(telefone)

    cpf_fmt = so_digitos(cpf)
    res = ResultadoEnvio(ok=False, cpf=cpf_fmt, regiao=regiao)

    page = context.new_page()
    try:
        print(f">> Movida pt1 | CPF/CNPJ {cpf_fmt} | regiao {regiao}")
        page.goto(config.LP_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        _fechar_cookies(page)

        page.locator("#name").scroll_into_view_if_needed()
        page.wait_for_timeout(300)

        print("   preenchendo dados...")
        page.locator("#name").fill(nome)
        page.locator("#cpf").fill(so_digitos(cpf))
        page.locator("#phone").fill(so_digitos(telefone))
        page.locator("#email").fill(email)

        print("   escolhendo carro...")
        res.carro_escolhido = _escolher_carro(page, carro)

        print(f"   regiao: {regiao}")
        page.select_option("#lp-cpa-region-select", label=regiao)

        print(f"   motorista de app: {driver_app} | contrato estendido: {contrato_estendido}")
        _marcar_radio(page, "lp-cpa-driver-yes" if driver_app.lower().startswith("s") else "lp-cpa-driver-no")
        _marcar_radio(page, "lp-cpa-extended-contract-yes" if contrato_estendido.lower().startswith("s") else "lp-cpa-extended-contract-no")

        print(f"   codigo do vendedor: {cod_vendedor}")
        try:
            page.locator(".clickVendedor").first.click(timeout=3000)
            page.wait_for_timeout(300)
        except Exception:
            pass
        page.locator("#VendedorID").fill(cod_vendedor, force=True)

        if not enviar:
            print("   [DRY-RUN] formulario preenchido — NAO vou clicar em Enviar.")
            conf = page.evaluate(
                """() => ({
                    name: document.querySelector('#name')?.value,
                    cpf: document.querySelector('#cpf')?.value,
                    phone: document.querySelector('#phone')?.value,
                    email: document.querySelector('#email')?.value,
                    carro: document.querySelector('#lp-cpa-vehicle-trigger')?.value,
                    regiao: document.querySelector('#lp-cpa-region-select')?.selectedOptions?.[0]?.text,
                    vendedor: document.querySelector('#VendedorID')?.value,
                    driver: (document.querySelector("input[name='lp-cpa-driver-app']:checked")||{}).id,
                    contrato: (document.querySelector("input[name='lp-cpa-extended-contract']:checked")||{}).id,
                })"""
            )
            print("   CONFERINDO valores preenchidos:")
            for k, v in conf.items():
                print(f"      {k:10}= {v!r}")
            if salvar_print:
                SAIDAS.mkdir(parents=True, exist_ok=True)
                p = SAIDAS / f"dryrun_{cpf_fmt or 'sem_cpf'}.png"
                page.screenshot(path=str(p), full_page=True)
                res.print_path = str(p)
            res.ok = True
            res.resposta = "[dry-run] formulario preenchido, envio nao realizado"
            return res

        print("   enviando (reCAPTCHA + POST /api/v5/lead)...")
        try:
            with page.expect_response(lambda r: "/api/v5/lead" in r.url, timeout=60000) as resp_info:
                page.locator("#btnSend").click()
            resp = resp_info.value
            res.status_http = resp.status
            try:
                res.resposta = resp.text()[:1000]
            except Exception:
                res.resposta = ""
            res.ok = 200 <= resp.status < 300
            print(f"   <- /api/v5/lead: HTTP {resp.status}")
        except PWTimeout:
            res.erro = "Timeout esperando /api/v5/lead (possivel bloqueio de reCAPTCHA)."
            print("   !! " + res.erro)

        page.wait_for_timeout(1500)
        if salvar_print:
            SAIDAS.mkdir(parents=True, exist_ok=True)
            p = SAIDAS / f"envio_{cpf_fmt or 'sem_cpf'}.png"
            page.screenshot(path=str(p), full_page=True)
            res.print_path = str(p)

    except Exception as e:
        res.erro = f"{type(e).__name__}: {e}"
        print(f"   !! ERRO: {res.erro}")
        if salvar_print:
            try:
                SAIDAS.mkdir(parents=True, exist_ok=True)
                p = SAIDAS / f"erro_{cpf_fmt or 'sem_cpf'}.png"
                page.screenshot(path=str(p), full_page=True)
                res.print_path = str(p)
            except Exception:
                pass
    finally:
        page.close()

    return res
