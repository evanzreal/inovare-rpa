"""
Unidas · precificacao.  [⏳ TODO — COMECAR POR AQUI: mais facil]

Da reuniao: tem botao "baixar tabela de preco" -> baixa a tabela COMPLETA,
todas as combinacoes. Sem 2FA. Menor risco de bloqueio (e download, nao consulta
repetida). So pessoa juridica por enquanto.

PENDENTE: URL logada, seletor do botao de download, parsear o arquivo -> LinhaPreco.
"""

from ....modelos import LinhaPreco


class Unidas:
    nome = "unidas"
    metodo = "download"

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("Unidas precificacao ainda nao implementada (download da tabela).")
