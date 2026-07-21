"""
Lista dos portais logados que o mantenedor de sessao deve manter ativos.
'cloudflare=True' = portal atras de Cloudflare (cuidar pra nao recarregar a toa).
"""

PORTAIS = [
    {"nome": "movida_b2b", "url": "https://portalb2b.movida.com.br/relatorios/pedidos", "cloudflare": True},
    {"nome": "localiza",   "url": "https://localiza.my.site.com/meoorevendas/s/"},
    {"nome": "byetech",    "url": "https://crm.byetech.pro/"},
    {"nome": "livre",      "url": "https://revendedor.livre.com.br/livre-para-voce/tabela-de-precos"},
    {
        "nome": "lm",
        "url": "https://portaldealer.lmmobilidade.com.br/orders",
        # LM salva as credenciais no cookie mas sempre abre modal "Entrar" ao carregar.
        # O mantenedor detecta o modal e clica automaticamente (sem digitar senha).
        "auto_login_botao": "button:has-text('Entrar'), input[type=submit][value='Entrar']",
    },
    {"nome": "nexia",      "url": "https://portal.nexiassessoria.com.br/auth/mobility/stellantis"},
]
