"""
Localiza · precificacao.  [⏳ TODO — a mais usada/importante]

Da reuniao: tem Excel completo pra baixar (todas as combinacoes: km, prazo, preco).
PORÉM pede fator de autenticacao (2FA) a cada 15 dias, e SO O SOCIO tem o
autenticador -> precisa coordenar o login nesses momentos. Logada, da pra raspar
sem nem filtrar (ja vem tudo).

Login feito pelo Guilherme em 2026-06-26.
Portal (Salesforce Experience Cloud): https://localiza.my.site.com/meoorevendas/s/

PENDENTE: pagina da tabela, download/raspagem, tratar o 2FA (avisar quando precisar).
"""

from ....modelos import LinhaPreco

PORTAL = "https://localiza.my.site.com/meoorevendas/s/"


class Localiza:
    nome = "localiza"
    metodo = "download"  # ou raspagem

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("Localiza precificacao ainda nao implementada (2FA a cada 15d).")
