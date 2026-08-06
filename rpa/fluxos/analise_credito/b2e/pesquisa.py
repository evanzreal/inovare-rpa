"""
B2E Group · Antifraude · Pesquisa por CPF.

Estratégia: navega direto via GET querystring (form server-rendered),
lê a tabela do DOM, retorna ResultadoCredito com o registro mais recente.
Fallback automático: se a sessão expirou e redireciona pro login,
clica Entrar (credenciais já salvas no perfil Chrome) e tenta de novo.
"""

from ....modelos import ResultadoCredito, STATUS_APROVADO, STATUS_REPROVADO, STATUS_ERRO
from ....util import so_digitos

PORTAL_URL = "https://webantifraudes.b2egroup.com.br/Web/Pesquisa"
_LOGIN_URL  = "https://webantifraudes.b2egroup.com.br/Web/Usuario/Login"

_MAPA_STATUS = {
    "aprovado automaticamente": STATUS_APROVADO,
    "aprovado":                 STATUS_APROVADO,
    "recusado automaticamente": STATUS_REPROVADO,
    "recusado":                 STATUS_REPROVADO,
}


def _mapear_status(texto: str) -> str:
    t = texto.lower()
    for chave, valor in _MAPA_STATUS.items():
        if chave in t:
            return valor
    return STATUS_ERRO


def _fazer_login(page) -> bool:
    """Clica Entrar na página de login (credenciais já pré-preenchidas pelo browser).
    Retorna True se a URL saiu da tela de login."""
    try:
        # Espera o botão aparecer antes de clicar
        page.wait_for_selector("input[type='submit']", timeout=10000)
        page.locator("input[type='submit']").click(timeout=8000)
        # Aguarda sair da tela de login (até 30s — portal pode demorar)
        page.wait_for_url(lambda u: _LOGIN_URL not in u, timeout=30000)
        return True
    except Exception:
        return _LOGIN_URL not in page.url


def _ler_tabela(page) -> list:
    linhas = page.evaluate("""() => {
        const rows = [...document.querySelectorAll('table tbody tr')];
        return rows.map(tr => ({
            colunas: [...tr.querySelectorAll('td')].map(td => td.innerText.trim())
        }));
    }""")
    return [l["colunas"] for l in linhas if len(l["colunas"]) >= 5 and l["colunas"][2]]


def buscar(cpf: str, context) -> ResultadoCredito:
    """
    Busca o CPF no portal B2E e retorna o registro mais recente.
    context: playwright PersistentContext (sessão pode ou não estar ativa).
    """
    cpf_limpo = so_digitos(cpf)
    url = f"{PORTAL_URL}?IDENTIFICADOR={cpf_limpo}"

    page = context.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(800)

        # Sessão expirada → redirecionou pro login
        if _LOGIN_URL in page.url:
            logou = _fazer_login(page)
            if not logou:
                return ResultadoCredito(
                    status=STATUS_ERRO,
                    locadora="b2e",
                    documento=cpf_limpo,
                    detalhe="Sessão expirada e login automático falhou",
                )
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(800)

        linhas_validas = _ler_tabela(page)

        if not linhas_validas:
            return ResultadoCredito(
                status=STATUS_REPROVADO,
                locadora="b2e",
                documento=cpf_limpo,
                detalhe="Nenhum registro encontrado no B2E para este CPF",
            )

        cols      = linhas_validas[0]
        data      = cols[0] if len(cols) > 0 else ""
        tipo      = cols[1] if len(cols) > 1 else ""
        status_raw = cols[5] if len(cols) > 5 else cols[-1]

        return ResultadoCredito(
            status=_mapear_status(status_raw),
            locadora="b2e",
            documento=cpf_limpo,
            detalhe=f"{status_raw} | {data} | {tipo}",
        )

    except Exception as exc:
        return ResultadoCredito(
            status=STATUS_ERRO,
            locadora="b2e",
            documento=cpf_limpo,
            detalhe=str(exc),
        )
    finally:
        page.close()
