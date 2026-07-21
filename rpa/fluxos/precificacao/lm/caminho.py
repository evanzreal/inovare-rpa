"""
LM · precificacao.  [⏳ TODO — a mais dificil, deixar quase por ultimo]

Da reuniao: estoque em TEMPO REAL. Tem que clicar na cor -> se houver preco
aparece o botao "assinar" -> configurar -> faixa 2 -> combinacoes. Posicao dos
carros NAO e fixa (muda a ordem), entao nao da pra confiar em posicao/pixel.
PF e PJ abrem paginas/layouts diferentes.

Login feito pelo Guilherme em 2026-06-26.
Portal dealer (pedidos): https://portaldealer.lmmobilidade.com.br/orders
(a tabela de precos em si fica em outra secao do portal — mapear depois.)

PENDENTE: URL da tabela, varredura por cor, faixa 2, ordem dinamica -> LinhaPreco.
"""

from ....modelos import LinhaPreco

PORTAL_PEDIDOS = "https://portaldealer.lmmobilidade.com.br/orders"


class LM:
    nome = "lm"
    metodo = "raspagem"

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("LM precificacao ainda nao implementada (tempo real, ordem dinamica).")
