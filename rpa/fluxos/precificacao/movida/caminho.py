"""
Movida · precificacao.  [⏳ TODO — POR ULTIMO]

Da reuniao: o Guilherme JA TEM o Excel da Movida (acesso interno), entao a
prioridade aqui e baixa. Quando for, da pra exportar/parsear esse Excel direto
em vez de raspar o site.

PENDENTE: ler o Excel existente da Movida -> LinhaPreco (padronizado).
"""

from ....modelos import LinhaPreco


class Movida:
    nome = "movida"
    metodo = "base"  # ja temos a base em Excel

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("Movida precificacao: usar o Excel ja existente (implementar depois).")
