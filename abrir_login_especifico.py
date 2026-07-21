"""
Abre o navegador do RPA em URLs especificas para relogar portais especificos.
Uso: python abrir_login_especifico.py <url1> <url2> ...
"""
import sys
from rpa.navegador import abrir_navegador

AVISO_HTML = """
<html><head><meta charset='utf-8'><title>RPA · aba de controle</title></head>
<body style='font-family:system-ui;background:#0f172a;color:#e2e8f0;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>
<div style='max-width:620px;text-align:center'>
  <h1 style='color:#fb923c;font-size:36px;margin:0 0 8px'>NÃO FECHE ESTA ABA</h1>
  <p style='font-size:18px;line-height:1.5'>
    Logue nas abas ao lado.<br>Quando terminar, feche a janela inteira.
  </p>
</div></body></html>
"""

urls = sys.argv[1:] if len(sys.argv) > 1 else []

def main():
    with abrir_navegador(headless=False) as context:
        controle = context.pages[0] if context.pages else context.new_page()
        controle.set_content(AVISO_HTML)
        for url in urls:
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print(f"Aberto com {len(urls)} aba(s) de login. Feche a janela quando terminar.")
        while True:
            try:
                controle.wait_for_timeout(1000)
                _ = controle.title()
            except Exception:
                break
    print(">> Sessao salva.")

if __name__ == "__main__":
    main()
