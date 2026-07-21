"""
Regioes aceitas pelas locadoras e deducao de regiao pelo DDD do cliente.
(Movida usa estes nomes; outras locadoras podem ter mapa proprio depois.)
"""

REGIOES = ["Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]

_DDD_REGIAO = {
    **{d: "Norte" for d in ["68", "92", "97", "96", "91", "93", "94", "69", "95", "63"]},
    **{d: "Nordeste" for d in ["82", "71", "73", "74", "75", "77", "85", "88", "98",
                               "99", "83", "81", "87", "86", "89", "84", "79"]},
    **{d: "Centro-Oeste" for d in ["61", "62", "64", "65", "66", "67"]},
    **{d: "Sudeste" for d in ["27", "28", "31", "32", "33", "34", "35", "37", "38",
                              "21", "22", "24", "11", "12", "13", "14", "15", "16",
                              "17", "18", "19"]},
    **{d: "Sul" for d in ["41", "42", "43", "44", "45", "46", "51", "53", "54", "55",
                          "47", "48", "49"]},
}


def regiao_por_ddd(telefone: str, padrao: str = "Sudeste") -> str:
    """Deduz a regiao a partir do DDD do telefone do cliente."""
    so = "".join(c for c in (telefone or "") if c.isdigit())
    if len(so) >= 2:
        return _DDD_REGIAO.get(so[:2], padrao)
    return padrao
