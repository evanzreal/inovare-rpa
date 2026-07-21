"""
Unidas · caminho de analise de credito.  [⏳ TODO]

Da reuniao:
  - E a MAIOR locadora, mas a analise e SEMI-MANUAL: da pra mandar alguns dados,
    e quando nao passa so com dados, vai por documentacao.
  - Regra geral: se nao passou na Movida nem na Localiza, dificilmente passa aqui.

PENDENTE: definir ate onde da pra automatizar o envio de dados.
"""

from ....modelos import Cliente, ResultadoCredito


class Unidas:
    nome = "unidas"
    automatico = False  # semi-manual / documentacao

    def consultar(self, cliente: Cliente, context, *, enviar: bool = False) -> ResultadoCredito:
        raise NotImplementedError("Unidas ainda nao implementada (semi-manual).")
