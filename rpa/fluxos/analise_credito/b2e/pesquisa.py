"""
B2E Group · Antifraude · Pesquisa por CPF/CNPJ.

Fluxo:
1. Navega via GET /Web/Pesquisa?IDENTIFICADOR={cpf_digitos}
2. Se sessão expirou → login automático → repete
3. Clica no primeiro resultado (linha mais recente) para abrir o detalhe
4. Lê o texto de "Impeditiva" na aba Alertas
5. Cruza com rpa/data/impeditivas.xlsx → retorna Proposta + OBS
"""

import re
import unicodedata

from ....modelos import ResultadoCredito, STATUS_APROVADO, STATUS_REPROVADO, STATUS_ERRO
from ....util import so_digitos
from ....navegador import RAIZ

PORTAL_URL = "https://webantifraudes.b2egroup.com.br/Web/Pesquisa"
_LOGIN_URL  = "https://webantifraudes.b2egroup.com.br/Web/Usuario/Login"

_MAPA_STATUS = {
    "aprovado automaticamente": STATUS_APROVADO,
    "aprovado":                 STATUS_APROVADO,
    "recusado automaticamente": STATUS_REPROVADO,
    "recusado":                 STATUS_REPROVADO,
}

# ──────────────────────────────────────────────
# Planilha de impeditivas
# ──────────────────────────────────────────────

_IMPEDITIVAS: list[dict] | None = None  # cache em memória


def _carregar_impeditivas() -> list[dict]:
    global _IMPEDITIVAS
    if _IMPEDITIVAS is not None:
        return _IMPEDITIVAS
    path = RAIZ / "rpa" / "data" / "impeditivas.xlsx"
    if not path.exists():
        _IMPEDITIVAS = []
        return _IMPEDITIVAS
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path))
        ws = wb.active
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            desc, prop, obs = (list(row) + [None, None, None])[:3]
            if desc:
                rows.append({
                    "descricao": str(desc).strip(),
                    "proposta":  str(prop).strip() if prop else "",
                    "obs":       str(obs).strip() if obs else "",
                })
        _IMPEDITIVAS = rows
    except Exception:
        _IMPEDITIVAS = []
    return _IMPEDITIVAS


def _normalizar(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


# Palavras muito genéricas que aparecem em quase todas as entradas — não discriminam
_STOPWORDS = {
    "com", "para", "uma", "mais", "entre", "igual", "por", "que", "do", "da",
    "de", "em", "ou", "e", "responsavel", "financeiro", "cliente", "renda",
    "loja", "valor",
}


def _match_impeditiva(alerta: str) -> dict | None:
    """
    Fuzzy match contra a planilha de impeditivas.
    Usa apenas palavras-chave distintas (>=5 chars, fora da stoplist).
    Retorna a linha com maior cobertura se >= 50% das palavras-chave baterem.
    """
    impeditivas = _carregar_impeditivas()
    if not impeditivas or not alerta:
        return None

    texto_norm = _normalizar(alerta)
    best, best_score = None, 0.0

    for imp in impeditivas:
        desc_norm = _normalizar(imp["descricao"])
        # Palavras com >= 3 chars que não estão na stoplist
        palavras = [p for p in re.split(r"\W+", desc_norm)
                    if len(p) >= 3 and p not in _STOPWORDS]
        if not palavras:
            continue
        hits = sum(1 for p in palavras if p in texto_norm)
        score = hits / len(palavras)
        if score > best_score:
            best_score = score
            best = imp

    if best and best_score >= 0.60:
        return {**best, "match_score": round(best_score, 2)}
    return None


# ──────────────────────────────────────────────
# Login automático
# ──────────────────────────────────────────────

def _fazer_login(page) -> bool:
    try:
        page.wait_for_selector("input[type='submit']", timeout=10000)
        page.locator("input[type='submit']").click(timeout=8000)
        page.wait_for_url(lambda u: _LOGIN_URL not in u, timeout=30000)
        return True
    except Exception:
        return _LOGIN_URL not in page.url


# ──────────────────────────────────────────────
# Leitura da tabela de resultados
# ──────────────────────────────────────────────

def _ler_tabela(page) -> list:
    linhas = page.evaluate("""() => {
        const rows = [...document.querySelectorAll('table tbody tr')];
        return rows.map(tr => ({
            colunas: [...tr.querySelectorAll('td')].map(td => td.innerText.trim())
        }));
    }""")
    return [l["colunas"] for l in linhas if len(l["colunas"]) >= 5 and l["colunas"][2]]


# ──────────────────────────────────────────────
# Detalhe do pedido: aba Alertas → Impeditiva
# ──────────────────────────────────────────────

def _ler_detalhe(page, cpf_limpo: str) -> dict:
    """
    Clica no primeiro resultado da lista e lê a aba Alertas.
    Retorna {"status_raw": "...", "alerta": "...", "impeditiva": {...}|None}.
    """
    # Aguarda tabela
    try:
        page.wait_for_selector("table tbody tr", timeout=8000)
    except Exception:
        return {"status_raw": "", "alerta": "", "impeditiva": None}

    # Lê status da primeira linha ANTES de navegar (para manter o status original)
    linhas = _ler_tabela(page)
    status_raw = ""
    if linhas:
        cols = linhas[0]
        status_raw = cols[5] if len(cols) > 5 else cols[-1]

    # Captura o nome do cliente do link antes de clicar
    nome_cliente = ""
    try:
        nome_cliente = page.locator("table tbody tr").first.locator("a").inner_text(timeout=4000).strip()
    except Exception:
        pass

    # Clica no link do nome (primeira linha)
    try:
        page.locator("table tbody tr").first.locator("a").click(timeout=8000)
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        return {"status_raw": status_raw, "alerta": "", "impeditiva": None, "nome": nome_cliente}

    # Aguarda aba Alertas (já vem selecionada por padrão)
    try:
        page.wait_for_selector("text=Impeditiva", timeout=8000)
    except Exception:
        pass

    # Lê texto da seção Impeditiva (aba Alertas)
    alerta = ""
    try:
        texto_pagina = page.evaluate("() => document.body.innerText") or ""
        m = re.search(r"Impeditiva\s+(.+?)(?=\n[A-ZÁÉÍÓÚÂÊÎÔÛÃÕ][a-záéíóúâêîôûãõ]|\Z)",
                      texto_pagina, re.DOTALL)
        if m:
            alerta = m.group(1).strip()
    except Exception:
        pass

    impeditiva_match = _match_impeditiva(alerta)

    # Aba Bureaux → CPF V2 Assertiva → nome real do cliente
    nome_real = nome_cliente
    try:
        page.get_by_role("tab", name="Bureaux").click(timeout=5000)
        page.wait_for_timeout(1500)
        # Clica em "CPF V2" ou "Assertiva" se houver botão
        for btn in ["Cpf V2 - Assertiva", "CPF V2 - Assertiva", "CPF V2", "Assertiva"]:
            try:
                page.get_by_role("button", name=btn, exact=False).first.click(timeout=3000)
                page.wait_for_timeout(1000)
                break
            except Exception:
                continue
        # Extrai o campo "Nome" do bureaux
        texto_bureaux = page.evaluate("() => document.body.innerText") or ""
        m = re.search(r"\bNome\b\s+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕ][A-ZÁÉÍÓÚÂÊÎÔÛÃÕ\s]+)", texto_bureaux)
        if m:
            nome_real = m.group(1).strip()
    except Exception:
        pass

    return {
        "status_raw": status_raw,
        "alerta":     alerta,
        "impeditiva": impeditiva_match,
        "nome":       nome_real,
    }


# ──────────────────────────────────────────────
# Função pública
# ──────────────────────────────────────────────

def _mapear_status(texto: str) -> str:
    t = texto.lower()
    for chave, valor in _MAPA_STATUS.items():
        if chave in t:
            return valor
    return STATUS_ERRO


def buscar(cpf: str, context) -> ResultadoCredito:
    """
    Busca CPF/CNPJ no B2E, clica no resultado mais recente,
    lê o alerta de Impeditiva e cruza com a planilha.
    """
    cpf_limpo = so_digitos(cpf)
    url = f"{PORTAL_URL}?IDENTIFICADOR={cpf_limpo}"

    page = context.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(800)

        # Sessão expirada → login automático
        if _LOGIN_URL in page.url:
            if not _fazer_login(page):
                return ResultadoCredito(
                    status=STATUS_ERRO, locadora="b2e", documento=cpf_limpo,
                    detalhe="Sessão expirada e login automático falhou",
                )
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(800)

        # Sem resultados
        linhas = _ler_tabela(page)
        if not linhas:
            return ResultadoCredito(
                status=STATUS_REPROVADO, locadora="b2e", documento=cpf_limpo,
                detalhe="Nenhum registro encontrado no B2E para este CPF",
            )

        # Abre detalhe e lê alerta
        detalhe_info = _ler_detalhe(page, cpf_limpo)
        status_raw   = detalhe_info["status_raw"] or (linhas[0][5] if len(linhas[0]) > 5 else linhas[0][-1])
        alerta       = detalhe_info["alerta"]
        imp          = detalhe_info["impeditiva"]

        cols  = linhas[0]
        data  = cols[0] if len(cols) > 0 else ""
        tipo  = cols[1] if len(cols) > 1 else ""

        detalhe_str = f"{status_raw} | {data} | {tipo}"
        if alerta:
            detalhe_str += f" | alerta: {alerta[:120]}"

        return ResultadoCredito(
            status=_mapear_status(status_raw),
            locadora="b2e",
            documento=cpf_limpo,
            detalhe=detalhe_str,
            bruto={
                "status_raw": status_raw,
                "data":       data,
                "tipo":       tipo,
                "alerta":     alerta,
                "impeditiva": imp,
            },
        )

    except Exception as exc:
        return ResultadoCredito(
            status=STATUS_ERRO, locadora="b2e", documento=cpf_limpo,
            detalhe=str(exc),
        )
    finally:
        page.close()
