"""
Contrato comum de um "caminho" de analise de credito.

Cada locadora (Movida, Localiza, Unidas, ...) implementa uma classe com este
formato. O pipeline roda todos eles para o mesmo cliente e agrega o resultado.
"""

from typing import Protocol, runtime_checkable

from ...modelos import Cliente, ResultadoCredito


@runtime_checkable
class CaminhoCredito(Protocol):
    nome: str          # identificador, ex.: "movida"
    automatico: bool   # True = a locadora devolve veredito automatico (Movida/Localiza)
                       # False = analise manual / so com documentacao (Unidas, etc.)

    def consultar(self, cliente: Cliente, context, *, enviar: bool = False) -> ResultadoCredito:
        """
        Roda a consulta de credito para o cliente nesta locadora.

        enviar=False -> modo seguro (dry-run): nao cria lead/consulta real.
        enviar=True  -> executa de verdade.
        """
        ...
