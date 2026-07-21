"""
Contrato comum de um "caminho" de precificacao.

Cada locadora coleta sua tabela de precos (download ou raspagem) e devolve uma
lista de LinhaPreco. O pipeline junta tudo, normaliza e gera uma base unica.
"""

from typing import Protocol, runtime_checkable

from ...modelos import LinhaPreco


@runtime_checkable
class CaminhoPreco(Protocol):
    nome: str
    metodo: str  # "download" (baixa Excel) | "raspagem" (le da tela) | "base" (ja temos)

    def coletar(self, context) -> list[LinhaPreco]:
        """Coleta a tabela de precos da locadora."""
        ...
