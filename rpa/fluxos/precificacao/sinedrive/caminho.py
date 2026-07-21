"""
SineDrive · precificacao.  [⏳ TODO]

Da reuniao: clicar, filtrar PF/PJ, selecionar -> aparecem todas as combinacoes
embaixo pra raspar. So pessoa juridica por enquanto. A sessao DESLOGA (cai),
entao precisa manter ativa / relogar.

PENDENTE: URL, fluxo de filtro PF/PJ, raspagem das combinacoes -> LinhaPreco.
"""

from ....modelos import LinhaPreco


class SineDrive:
    nome = "sinedrive"
    metodo = "raspagem"

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("SineDrive precificacao ainda nao implementada.")
