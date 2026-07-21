# Portais e logins (perfil `.perfil_chrome/`)

Logins salvos pelo Guilherme em 2026-06-26. Reusados pelo navegador do RPA.
⚠️ Alguns têm Cloudflare (rodar headed) / 2FA. Sessão cai se ficar inativa.

| Sistema | URL | Fluxo / uso | Obs. |
|---|---|---|---|
| **Byetech (cotação)** | https://crm.byetech.pro/ (Comercial > Cotações) | **Precificação · AGREGADOR** de várias locadoras | preencher filtros e raspar; não enviar |
| **Movida** (B2B) | https://portalb2b.movida.com.br/relatorios/pedidos | Crédito · pt2 (ler status "Meus Pedidos") | ⚠️ Cloudflare → headed |
| **Movida** (LP) | https://www.movidacarroporassinatura.com.br/lp/carro-por-assinatura/ | Crédito · pt1 (envio do lead) ✅ | reCAPTCHA Enterprise |
| **Localiza** | https://localiza.my.site.com/meoorevendas/s/ | Crédito (consultar + travar) e Precificação | Salesforce; 2FA a cada 15d (só sócio) |
| **Livre** | https://revendedor.livre.com.br/livre-para-voce/tabela-de-precos | Precificação (tabela) | locadora nova |
| **LM Mobilidade** | https://portaldealer.lmmobilidade.com.br/orders | Pedidos; preço em outra seção | tabela tempo real |
| **Nexia (Stellantis)** | https://portal.nexiassessoria.com.br/auth/mobility/stellantis | Precificação (confirmar) | carros Stellantis |
| _Unidas_ | _(pendente login)_ | Crédito (semi) + Precificação (download) | — |
| _SineDrive_ | _(pendente login)_ | Precificação (raspagem) | sessão cai |

## Como verificar uma sessão
```bash
source .venv/bin/activate
python verificar_login.py "<url>" --headed
```
