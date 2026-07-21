"""
Livre · precificacao.  [⏳ TODO — locadora nova, tem TABELA DE PRECOS logada]

Login feito pelo Guilherme em 2026-06-26.
URL da tabela: https://revendedor.livre.com.br/livre-para-voce/tabela-de-precos

PENDENTE: inspecionar a tela (download? raspagem?), mapear e gerar LinhaPreco.
"""

from ....modelos import LinhaPreco

URL_TABELA = "https://revendedor.livre.com.br/livre-para-voce/tabela-de-precos"


class Livre:
    nome = "livre"
    metodo = "raspagem"  # confirmar: pode ter download

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("Livre precificacao ainda nao implementada (mapear tabela de precos).")
