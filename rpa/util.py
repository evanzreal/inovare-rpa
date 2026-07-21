"""Helpers genericos usados em varios lugares."""


def so_digitos(txt: str) -> str:
    """Mantem apenas digitos de uma string (CPF, CNPJ, telefone)."""
    return "".join(c for c in (txt or "") if c.isdigit())


def eh_cnpj(documento: str) -> bool:
    """True se o documento tem cara de CNPJ (14 digitos) e nao de CPF (11)."""
    return len(so_digitos(documento)) > 11
