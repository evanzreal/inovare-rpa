"""
Dataclasses compartilhadas pelos dois fluxos.

Cliente            -> entrada (vem do CRM/WhatsApp)
ResultadoCredito   -> saida do fluxo de analise de credito (por locadora)
LinhaPreco         -> saida do fluxo de precificacao (uma combinacao de preco)
"""

from dataclasses import dataclass, field

from .util import so_digitos, eh_cnpj

# status possiveis de uma consulta de credito
STATUS_ENVIADO = "enviado"      # lead enviado, retorno ainda nao lido (ex.: Movida pt1)
STATUS_APROVADO = "aprovado"
STATUS_REPROVADO = "reprovado"
STATUS_REANALISE = "reanalise"  # reprovado, mas aceita reanalise com documento
STATUS_PENDENTE = "pendente"    # caminho ainda nao implementado
STATUS_ERRO = "erro"


@dataclass
class Cliente:
    """Cliente que chega pra analise. 'documento' = CPF ou CNPJ."""
    nome: str
    documento: str
    telefone: str | None = None
    regiao: str | None = None
    origem: str = ""  # ex.: id do card no CRM

    @property
    def eh_cnpj(self) -> bool:
        return eh_cnpj(self.documento)

    @property
    def documento_digitos(self) -> str:
        return so_digitos(self.documento)


@dataclass
class ResultadoCredito:
    """Resultado de UM caminho (locadora) pra UM cliente."""
    locadora: str
    documento: str
    status: str = STATUS_PENDENTE
    detalhe: str = ""
    status_http: int | None = None
    print_path: str = ""
    bruto: dict = field(default_factory=dict)


@dataclass
class LinhaPreco:
    """Uma combinacao de preco coletada de uma locadora."""
    locadora: str
    modelo: str
    versao: str = ""
    pessoa: str = ""           # "fisica" | "juridica"
    meses: int | None = None
    km_mes: int | None = None  # franquia de km/mes
    preco: float | None = None
    bruto: dict = field(default_factory=dict)
