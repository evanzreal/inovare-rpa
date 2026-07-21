"""
Pipeline de PRECIFICACAO.

Roda os caminhos (locadoras), normaliza cada linha e junta numa base unica
pronta pra virar o Excel que as vendedoras filtram.

Ordem por facilidade (da reuniao): Unidas e Fluor primeiro; LM e Movida por ultimo.
Caminhos nao implementados sao pulados (com aviso), sem quebrar o fluxo.
"""

from ...modelos import LinhaPreco
from .normalizacao import normalizar
from .unidas.caminho import Unidas
from .fluor.caminho import Fluor
from .sinedrive.caminho import SineDrive
from .localiza.caminho import Localiza
from .lm.caminho import LM
from .movida.caminho import Movida
from .livre.caminho import Livre
from .byetech.caminho import Byetech
from .nexia.caminho import Nexia

# Byetech 1o: agregador que pode trazer varias locadoras de uma vez.
CAMINHOS = [Byetech(), Unidas(), Fluor(), SineDrive(), Livre(), Nexia(), Localiza(), LM(), Movida()]


def rodar(context, *, apenas: list[str] | None = None) -> list[LinhaPreco]:
    """
    Coleta precos de todas as locadoras (ou so as de 'apenas') e devolve a base
    normalizada. 'apenas' = lista de nomes, ex.: ["unidas", "fluor"].
    """
    base: list[LinhaPreco] = []
    for caminho in CAMINHOS:
        if apenas and caminho.nome not in apenas:
            continue
        try:
            linhas = caminho.coletar(context)
            base.extend(normalizar(l) for l in linhas)
            print(f"   [{caminho.nome}] {len(linhas)} linhas coletadas")
        except NotImplementedError as e:
            print(f"   [{caminho.nome}] PENDENTE: {e}")
        except Exception as e:
            print(f"   [{caminho.nome}] ERRO: {type(e).__name__}: {e}")
    return base
