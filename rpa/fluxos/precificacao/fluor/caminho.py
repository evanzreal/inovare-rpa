"""
Fluor (Flua) · precificacao.  [⏳ TODO — facil]

Da reuniao: tudo ja esta na tela; basta abrir as "caixinhas" e raspar. Apos
entrar na pagina, raspa direto. Tem so uma "bolinha"/loader, mas nao cai.

PENDENTE: URL, abrir as secoes e raspar a tabela -> LinhaPreco.
"""

from ....modelos import LinhaPreco


class Fluor:
    nome = "fluor"
    metodo = "raspagem"

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("Fluor precificacao ainda nao implementada (raspagem da tela).")
