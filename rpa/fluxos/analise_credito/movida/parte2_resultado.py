"""
Movida · Análise de crédito · PARTE 2 — LER O RESULTADO.  [⏳ TODO]

Onde mora o ouro: depois do envio (parte 1), o veredito aprovado/reprovado
aparece no PORTAL LOGADO do vendedor. Aqui a gente abre esse portal (sessao ja
logada no perfil persistente), localiza o lead recem-criado e le o status.

Da reuniao: "aperta CPF -> avancar -> botar dados -> avancar -> aguardar
~10-15s -> vem reprovado/aprovado". Pode ser que o proprio portal tenha uma
consulta direta de CPF que devolve o veredito na hora (a confirmar com o
Guilherme abrindo o portal logado pra mapearmos os seletores).

PENDENTE pra implementar:
  - URL do portal logado do vendedor.
  - Seletor do campo de busca por CPF/lead e do badge de status.
  - Regra de reanalise (reprovado que aceita documentacao).
"""

from ....modelos import ResultadoCredito, STATUS_PENDENTE


def ler_resultado(documento: str, context) -> ResultadoCredito:
    raise NotImplementedError(
        "Movida parte 2 ainda nao implementada. Precisamos abrir o portal logado "
        "do vendedor pra mapear os seletores do veredito (aprovado/reprovado)."
    )
