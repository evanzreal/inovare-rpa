"""
Verifica se o perfil persistente continua LOGADO numa URL.

Abre a URL no navegador do RPA (headless) e checa se caiu numa tela de login
(campo de senha / palavra 'login' na URL) ou se entrou de fato. Salva um print.

Uso:
    python verificar_login.py <URL>
"""

import sys
from pathlib import Path

from rpa.navegador import abrir_navegador, RAIZ

SAIDAS = RAIZ / "saidas"
args = [a for a in sys.argv[1:] if a != "--headed"]
HEADED = "--headed" in sys.argv
URL = args[0] if args else "https://portalb2b.movida.com.br/relatorios/pedidos"


def main():
    SAIDAS.mkdir(exist_ok=True)
    with abrir_navegador(headless=not HEADED) as context:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # espera o Cloudflare resolver sozinho (ate ~25s)
        cf = False
        for _ in range(25):
            page.wait_for_timeout(1000)
            t = (page.title() or "").lower()
            corpo = page.inner_text("body")[:400].lower() if page.locator("body").count() else ""
            cf = ("momento" in t or "moment" in t or "confirme que" in corpo
                  or "não é um robô" in corpo or "nao e um robo" in corpo)
            if not cf:
                break

        url_final = page.url
        titulo = page.title()
        tem_senha = page.locator("input[type=password]").count() > 0
        url_login = any(p in url_final.lower() for p in ["login", "signin", "auth", "entrar"])
        logado = not (tem_senha or url_login or cf)
        print(f">> Cloudflare bloqueando: {cf}")

        print(f">> URL pedida : {URL}")
        print(f">> URL final  : {url_final}")
        print(f">> Titulo     : {titulo}")
        print(f">> Campo senha: {tem_senha} | URL de login: {url_login}")
        print(f">> LOGADO?    : {'✅ SIM' if logado else '❌ NAO (precisa logar de novo)'}")

        p = SAIDAS / "verificar_login.png"
        page.screenshot(path=str(p), full_page=True)
        print(f">> Print: {p}")


if __name__ == "__main__":
    main()
