# Estrutura do RPA Inovare

Dois fluxos guarda-chuva. Cada locadora é um **caminho** independente; o
**pipeline** de cada fluxo roda todos os caminhos e junta o resultado.

```
rpa/
├── navegador.py        navegador com perfil logado persistente (.perfil_chrome/)
├── util.py             helpers (so_digitos, eh_cnpj)
├── modelos.py          Cliente, ResultadoCredito, LinhaPreco (+ status)
└── fluxos/
    ├── analise_credito/         ───── FLUXO 1
    │   ├── base.py              contrato CaminhoCredito (consultar)
    │   ├── regioes.py          região por DDD
    │   ├── pipeline.py         roda Movida→Localiza→Unidas p/ um cliente, agrega
    │   ├── movida/
    │   │   ├── config.py            valores fixos (tel, email, cod vendedor, carro)
    │   │   ├── parte1_envio.py      ✅ envia o lead (dispara análise)
    │   │   ├── parte2_resultado.py  ⏳ lê aprovado/reprovado no portal logado
    │   │   └── caminho.py           junta pt1 + pt2
    │   ├── localiza/caminho.py  ⏳ CPF/CNPJ automático + travar cliente (15d)
    │   └── unidas/caminho.py    ⏳ semi-manual
    └── precificacao/            ───── FLUXO 2
        ├── base.py             contrato CaminhoPreco (coletar)
        ├── normalizacao.py     de-para nomes/meses/km → base única
        ├── pipeline.py         roda todos, normaliza, concatena
        ├── unidas/    ⏳ download tabela (MAIS FÁCIL — começar aqui)
        ├── fluor/     ⏳ raspar tela (fácil)
        ├── sinedrive/ ⏳ filtrar PF/PJ + raspar (sessão cai)
        ├── localiza/  ⏳ download Excel (2FA a cada 15d, só sócio tem)
        ├── lm/        ⏳ tempo real, ordem dinâmica (mais difícil)
        └── movida/    ⏳ já tem Excel interno (por último)
```

## Entrypoints (rodar da raiz, com a venv ativa)

```bash
source .venv/bin/activate

# logar nas locadoras (abre navegador; feche a janela ao terminar)
python abrir_login.py

# inspecionar uma tela (salva campos/print/html em saidas/)
python inspecionar.py "<url>"

# Movida pt1 — preencher SEM enviar (dry-run, seguro):
python enviar_movida.py --nome "Cliente" --cpf 111.444.777-35 --regiao Sudeste

# Movida pt1 — enviar de verdade:
python enviar_movida.py --nome "Cliente" --cpf 123.456.789-00 --regiao Norte --enviar
```

## Status
- ✅ **Movida · crédito · pt1 (envio)** — feito e validado (dry-run).
- ⏳ Movida · crédito · pt2 (ler veredito no portal) — precisa do portal logado.
- ⏳ Localiza/Unidas crédito; todo o fluxo de precificação.

## Notas técnicas
- LP da Movida envia `POST /api/v5/lead` protegido por **reCAPTCHA Enterprise**
  (invisível/score) → tem que dirigir navegador real; IP datacenter/headless
  derruba o score (produção: VM + proxy residencial).
- Movida ~10 consultas por IP; ir devagar (anti-fraude).
```
