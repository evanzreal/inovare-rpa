"""
Movida · caminho de analise de credito = PARTE 1 (envio) + PARTE 2 (resultado).

Implementa o contrato CaminhoCredito (base.py). Hoje so a parte 1 esta pronta,
entao consultar() envia o lead e retorna status "enviado". Quando a parte 2
ficar pronta, ele tambem le o veredito e retorna aprovado/reprovado.
"""

from ....modelos import Cliente, ResultadoCredito, STATUS_ENVIADO, STATUS_ERRO
from .parte1_envio import enviar_lead
from . import parte2_resultado


class Movida:
    nome = "movida"
    automatico = True  # Movida devolve veredito automatico (na parte 2)

    def consultar(self, cliente: Cliente, context, *, enviar: bool = False, ler_resultado: bool = False) -> ResultadoCredito:
        env = enviar_lead(
            nome=cliente.nome,
            cpf=cliente.documento,
            regiao=cliente.regiao,
            context=context,
            enviar=enviar,
        )
        res = ResultadoCredito(
            locadora=self.nome,
            documento=env.cpf,
            status=STATUS_ENVIADO if env.ok else STATUS_ERRO,
            detalhe=env.erro or env.resposta,
            status_http=env.status_http,
            print_path=env.print_path,
            bruto={"carro": env.carro_escolhido, "regiao": env.regiao},
        )
        # PARTE 2 (quando implementada): le o veredito no portal logado.
        if enviar and ler_resultado:
            try:
                veredito = parte2_resultado.ler_resultado(env.cpf, context)
                res.status = veredito.status
                res.detalhe = veredito.detalhe or res.detalhe
            except NotImplementedError as e:
                res.detalhe += f" | parte2 pendente: {e}"
        return res
