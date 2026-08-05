"""
B2E Group · Antifraude · Pesquisa por CPF.

Assume que o contexto já está autenticado em:
  https://webantifraudes.b2egroup.com.br/Web/Pesquisa

Estratégia: navega direto via GET querystring (form server-rendered),
lê a tabela do DOM, retorna ResultadoCredito com o registro mais recente.
"""

from ....modelos import ResultadoCredito, STATUS_APROVADO, STATUS_REPROVADO, STATUS_ERRO
from ....util import so_digitos

PORTAL_URL = "https://webantifraudes.b2egroup.com.br/Web/Pesquisa"

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


def buscar(cpf: str, context) -> ResultadoCredito:
    """
    Busca o CPF no portal B2E e retorna o registro mais recente.
    context: playwright PersistentContext já autenticado.
    """
    cpf_limpo = so_digitos(cpf)
    url = f"{PORTAL_URL}?IDENTIFICADOR={cpf_limpo}"

    page = context.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1000)

        # Lê linhas da tabela (HTML server-rendered)
        linhas = page.evaluate("""() => {
            const rows = [...document.querySelectorAll('table tbody tr')];
            return rows.map(tr => ({
                colunas: [...tr.querySelectorAll('td')].map(td => td.innerText.trim())
            }));
        }""")

        # Filtra linhas com conteúdo real (descarta "Nenhum registro encontrado")
        linhas_validas = [
            l["colunas"] for l in linhas
            if len(l["colunas"]) >= 5 and l["colunas"][2]  # tem nome
        ]

        if not linhas_validas:
            return ResultadoCredito(
                status=STATUS_REPROVADO,
                locadora="b2e",
                detalhe="Nenhum registro encontrado no B2E para este CPF",
            )

        # Primeiro registro = mais recente
        cols = linhas_validas[0]
        data   = cols[0] if len(cols) > 0 else ""
        tipo   = cols[1] if len(cols) > 1 else ""
        nome   = cols[2] if len(cols) > 2 else ""
        status_raw = cols[5] if len(cols) > 5 else cols[-1]

        status = _mapear_status(status_raw)

        return ResultadoCredito(
            status=status,
            locadora="b2e",
            detalhe=f"{status_raw} | {data} | {tipo}",
            documento=cpf_limpo,
        )

    except Exception as exc:
        return ResultadoCredito(
            status=STATUS_ERRO,
            locadora="b2e",
            detalhe=str(exc),
        )
    finally:
        page.close()
