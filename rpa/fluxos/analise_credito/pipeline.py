"""
Pipeline de ANALISE DE CREDITO.

Roda os caminhos (locadoras) para o mesmo cliente e agrega o resultado.
Como diz a reuniao: o cliente pode reprovar numa e aprovar noutra — entao a
saida e uma lista de ResultadoCredito, um por locadora.

Regras:
  - Movida so aceita CPF -> e pulada quando o documento e CNPJ.
  - Caminhos ainda nao implementados retornam status "pendente" (nao quebram o fluxo).
  - Execucao sequencial de proposito (cada consulta gasta cota por IP; ir devagar
    reduz risco de bloqueio/anti-fraude).
"""

from ...modelos import Cliente, ResultadoCredito, STATUS_PENDENTE, STATUS_ERRO
from .movida.caminho import Movida
from .localiza.caminho import Localiza
from .unidas.caminho import Unidas

# Ordem dos caminhos no pipeline. Movida 1o (mais simples), depois Localiza, Unidas.
CAMINHOS = [Movida(), Localiza(), Unidas()]


def rodar(cliente: Cliente, context, *, enviar: bool = False) -> list[ResultadoCredito]:
    resultados: list[ResultadoCredito] = []
    for caminho in CAMINHOS:
        # Movida nao aceita CNPJ.
        if caminho.nome == "movida" and cliente.eh_cnpj:
            resultados.append(ResultadoCredito(
                locadora=caminho.nome, documento=cliente.documento_digitos,
                status=STATUS_PENDENTE, detalhe="Movida nao aceita CNPJ (so CPF)."))
            continue
        try:
            resultados.append(caminho.consultar(cliente, context, enviar=enviar))
        except NotImplementedError as e:
            resultados.append(ResultadoCredito(
                locadora=caminho.nome, documento=cliente.documento_digitos,
                status=STATUS_PENDENTE, detalhe=str(e)))
        except Exception as e:
            resultados.append(ResultadoCredito(
                locadora=caminho.nome, documento=cliente.documento_digitos,
                status=STATUS_ERRO, detalhe=f"{type(e).__name__}: {e}"))
    return resultados
