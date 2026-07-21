"""
Normalizacao / de-para da precificacao.  [⏳ TODO]

Da reuniao: cada locadora nomeia o carro de um jeito e formata mes/km de outro.
Aqui a gente padroniza tudo (ex.: nome do modelo em maiusculas, "12" meses,
"1000" km/mes) pra base final ficar filtravel pelas vendedoras num Excel unico.
"""

from ...modelos import LinhaPreco


def normalizar(linha: LinhaPreco) -> LinhaPreco:
    """Padroniza nome do modelo, meses e km de UMA linha. [⏳ TODO refinar de-para]"""
    if linha.modelo:
        linha.modelo = linha.modelo.strip().upper()
    return linha
