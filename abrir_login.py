"""
Abre o navegador do RPA pra voce LOGAR nas locadoras.

Mantem uma ABA DE CONTROLE fixa aberta pra o navegador NAO fechar quando voce
fecha suas abas de login. Abra outras abas (Ctrl+T) pra logar nas locadoras.
O login fica gravado em .perfil_chrome/ e o RPA reusa depois.

Para encerrar: feche a janela inteira do navegador, ou pare este processo.
"""

from rpa.navegador import abrir_navegador

AVISO_HTML = """
<html><head><meta charset='utf-8'><title>RPA · aba de controle</title></head>
<body style='font-family:system-ui;background:#0f172a;color:#e2e8f0;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>
<div style='max-width:620px;text-align:center'>
  <h1 style='color:#fb923c;font-size:42px;margin:0 0 8px'>NÃO FECHE ESTA ABA</h1>
  <p style='font-size:20px;line-height:1.5'>
    Esta aba mantém o navegador aberto.<br>
    Abra <b>outras abas (Ctrl+T)</b> e faça login nas locadoras normalmente.<br>
    Pode abrir e fechar as outras abas à vontade — o navegador não vai fechar.
  </p>
  <p style='font-size:16px;color:#94a3b8'>
    Quando terminar de logar em tudo, feche a janela inteira (ou avise o RPA).
  </p>
</div></body></html>
"""


def main():
    with abrir_navegador(headless=False) as context:
        # aba de controle fixa (nunca fechamos) — segura o navegador aberto
        controle = context.pages[0] if context.pages else context.new_page()
        controle.set_content(AVISO_HTML)

        print("=" * 60)
        print("  Navegador aberto. ABRA OUTRAS ABAS (Ctrl+T) pra logar.")
        print("  A aba de controle segura o navegador — nao feche so ela.")
        print("=" * 60)

        # mantem vivo ate o navegador ser fechado de fato (janela inteira)
        while True:
            try:
                controle.wait_for_timeout(1000)
                _ = controle.title()  # se o navegador morreu, isso lanca erro
            except Exception:
                break

    print(">> Sessao salva em .perfil_chrome/. Pode fechar este terminal.")


if __name__ == "__main__":
    main()
