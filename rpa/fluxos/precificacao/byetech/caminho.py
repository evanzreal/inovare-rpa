"""
Byetech · precificacao.  [⏳ TODO — AGREGADOR: potencialmente o caminho mais valioso]

NAO e o CRM. E uma ferramenta de COTACAO que ja AGREGA precos de varias locadoras
numa tela so (menu Comercial > Cotacoes > "Criar cotacao").

Login feito pelo Guilherme em 2026-06-26.
Base: https://crm.byetech.pro/  (cotacao em Comercial > Cotacoes)

Tela "Criar cotacao":
  - filtros: Tipo de contrato (PF/PJ), Franquia*, Tempo de contrato, Locadora
    (multi-selecao), Categoria, Budget min/max, Nome do modelo.
  - lista cards "a partir de R$ X" por veiculo, com selo da locadora (ex.: "Localiza Meoo").
    "Mostrando 12 de 200 veiculos"; ordena por maior/menor preco.
  - cada card abre detalhe (icones) com as combinacoes; botao "Gerar cotacao".
  - botao "Atualizacao de precos" (forca refresh).

IDEIA: preencher filtros e RASPAR (sem enviar/gerar nada) -> precos por locadora
de uma vez. Pode reduzir muito a necessidade de raspar cada site separado — A
CONFIRMAR quais locadoras o Byetech cobre e se traz todas as combinacoes (mes x km).

PENDENTE: inspecionar a tela logada, mapear filtros/cards/detalhe -> LinhaPreco
(preencher locadora a partir do selo do card).
"""

from ....modelos import LinhaPreco

BASE = "https://crm.byetech.pro/"


class Byetech:
    nome = "byetech"
    metodo = "raspagem"

    def coletar(self, context) -> list[LinhaPreco]:
        raise NotImplementedError("Byetech (agregador de cotacao) ainda nao implementado.")
