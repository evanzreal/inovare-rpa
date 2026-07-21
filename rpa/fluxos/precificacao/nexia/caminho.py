"""
Nexia Assessoria (Stellantis mobility) · precificacao.  [⏳ TODO — confirmar fluxo]

Login feito pelo Guilherme em 2026-06-26.
URL: https://portal.nexiassessoria.com.br/auth/mobility/stellantis
Provavelmente assinatura/precos de veiculos Stellantis (Fiat, Jeep, Peugeot, Citroen, RAM).

A CONFIRMAR: e precificacao (tabela) e/ou tambem analise de credito? Mapear ao inspecionar.
"""

from ....modelos import LinhaPreco

URL = "https://portal.nexiassessoria.com.br/auth/mobility/stellantis"


class Nexia:
    nome = "nexia"
    metodo = "raspagem"

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("Nexia (Stellantis) ainda nao implementada — confirmar fluxo.")
