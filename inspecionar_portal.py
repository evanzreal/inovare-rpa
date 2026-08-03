"""Inspeciona os seletores do portal B2B Movida — roda uma vez e salva JSON."""
import json
from rpa.navegador import abrir_navegador

URL = "https://portalb2b.movida.com.br/relatorios/pedidos"

with abrir_navegador(headless=False) as ctx:
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    # espera o Angular renderizar as linhas da tabela
    try:
        page.wait_for_selector("mat-row, tr.mat-row, [role='row']", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(3000)

    info = page.evaluate("""() => {
        const inputs = [...document.querySelectorAll('input')].map(el => ({
            tag: 'input',
            id: el.id,
            name: el.name,
            placeholder: el.placeholder,
            type: el.type,
            class: el.className.slice(0, 80),
        }));
        const rows = [...document.querySelectorAll('table tr, mat-row, .cdk-row')].slice(0, 5).map(r => r.innerText.trim().slice(0, 200));
        const cols = [...document.querySelectorAll('th, mat-header-cell, .cdk-header-cell')].map(c => c.innerText.trim());
        return { inputs, rows, cols };
    }""")

    with open("saidas/portal_b2b_seletores.json", "w") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print("Salvo em saidas/portal_b2b_seletores.json")
    print("\n=== COLUNAS ===")
    for c in info["cols"]:
        print(" ", c)
    print("\n=== INPUTS ===")
    for i in info["inputs"]:
        print(" ", i)
    print("\n=== PRIMEIRAS LINHAS ===")
    for r in info["rows"]:
        print(" ", r[:120])
    page.close()
