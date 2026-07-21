"""
Entrypoint: Movida · Análise de crédito · Parte 1 (envio do lead).

Exemplos:
  # DRY-RUN (preenche tudo, NAO envia) — padrao seguro:
  python enviar_movida.py --nome "Joao Teste" --cpf 111.444.777-35 --regiao Sudeste

  # ENVIO REAL (cria o lead e dispara a analise):
  python enviar_movida.py --nome "Joao Teste" --cpf 123.456.789-00 --regiao Nordeste --enviar
"""

import argparse

from rpa.navegador import abrir_navegador
from rpa.fluxos.analise_credito.regioes import REGIOES
from rpa.fluxos.analise_credito.movida.parte1_envio import enviar_lead


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nome", required=True, help="Nome do cliente")
    ap.add_argument("--cpf", required=True, help="CPF ou CNPJ do cliente")
    ap.add_argument("--regiao", default=None, choices=REGIOES,
                    help="Regiao (se omitir, deduz pelo DDD do telefone fixo)")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", help="Preenche mas NAO envia (padrao)")
    grp.add_argument("--enviar", action="store_true", help="Envia de verdade (cria lead)")
    ap.add_argument("--headless", action="store_true", help="Sem janela (evite em teste)")
    ap.add_argument("--devagar", type=int, default=300, help="ms entre acoes")
    args = ap.parse_args()

    enviar = bool(args.enviar)
    modo = "ENVIO REAL" if enviar else "DRY-RUN (nao envia)"
    print("=" * 60)
    print(f"  MOVIDA pt1 — {modo}")
    print(f"  nome={args.nome!r} cpf={args.cpf!r} regiao={args.regiao or '(auto DDD)'}")
    print("=" * 60)

    with abrir_navegador(headless=args.headless, slow_mo=args.devagar) as context:
        res = enviar_lead(
            nome=args.nome, cpf=args.cpf, regiao=args.regiao,
            context=context, enviar=enviar,
        )

    print("\n----- RESULTADO -----")
    print(f"  ok............: {res.ok}")
    print(f"  carro.........: {res.carro_escolhido}")
    print(f"  regiao........: {res.regiao}")
    print(f"  status_http...: {res.status_http}")
    print(f"  resposta......: {res.resposta[:300]}")
    if res.erro:
        print(f"  erro..........: {res.erro}")
    print(f"  print.........: {res.print_path}")


if __name__ == "__main__":
    main()
