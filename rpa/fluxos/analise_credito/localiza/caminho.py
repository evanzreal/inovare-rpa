"""
Localiza · caminho de analise de credito.  [⏳ TODO]

Da reuniao:
  - Aceita CPF E CNPJ (Movida so CPF). Analise automatica, ~10-15s.
  - Login com senha (sessao cai se ficar inativa -> manter script ativo).
  - Formatacao OBRIGATORIA com pontos/traco no CPF/CNPJ.
  - APROVADO -> TRAVAR o cliente (reserva 15 dias):
      converter -> nova proposta -> escolher carro padrao -> pintura solida
      -> calcular -> adicionar -> salvar -> enviar por e-mail.
  - Quer travar TODOS os aprovados (inclusive os ultimos ~2-3 meses) e re-travar
    periodicamente pra ninguem ser liberado.
  - Localiza e rigorosa com valor (mensalidade alta dificil de aprovar).

Login feito pelo Guilherme em 2026-06-26.
Portal (Salesforce Experience Cloud): https://localiza.my.site.com/meoorevendas/s/

PENDENTE: paginas internas de consulta, badge de status e sequencia de travamento.
"""

from ....modelos import Cliente, ResultadoCredito

PORTAL = "https://localiza.my.site.com/meoorevendas/s/"


class Localiza:
    nome = "localiza"
    automatico = True

    def consultar(self, cliente: Cliente, context, *, enviar: bool = False) -> ResultadoCredito:
        raise NotImplementedError("Localiza ainda nao implementada (ver docstring).")

    def travar_cliente(self, cliente: Cliente, context):
        """Reserva o cliente aprovado por 15 dias. [⏳ TODO]"""
        raise NotImplementedError("Travamento de cliente na Localiza ainda nao implementado.")
