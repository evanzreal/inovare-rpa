"""
Inspetor de telas: abre uma URL no navegador do RPA, rola a pagina toda e
lista todos os campos de formulario (inputs, selects, textareas, botoes).
Salva tambem um print e o HTML em saidas/ pra analise.

Uso:
    python inspecionar.py <URL>
"""

import sys
import json
from pathlib import Path

from rpa.navegador import abrir_navegador, RAIZ

SAIDAS = RAIZ / "saidas"

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.movidacarroporassinatura.com.br/lp/carro-por-assinatura/"

# JS que extrai a estrutura dos campos visiveis na pagina (e dentro de iframes).
JS_EXTRAIR = r"""
() => {
  function visivel(el) {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  }
  function rotulo(el) {
    if (el.labels && el.labels.length) return el.labels[0].innerText.trim();
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label').trim();
    if (el.id) {
      const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (l) return l.innerText.trim();
    }
    return '';
  }
  const out = { inputs: [], selects: [], textareas: [], botoes: [] };
  document.querySelectorAll('input').forEach(el => {
    if (!visivel(el)) return;
    out.inputs.push({
      type: el.type, name: el.name || '', id: el.id || '',
      placeholder: el.placeholder || '', label: rotulo(el),
      required: el.required, value: el.value || ''
    });
  });
  document.querySelectorAll('select').forEach(el => {
    if (!visivel(el)) return;
    out.selects.push({
      name: el.name || '', id: el.id || '', label: rotulo(el),
      options: Array.from(el.options).slice(0, 30).map(o => ({ value: o.value, text: o.text.trim() }))
    });
  });
  document.querySelectorAll('textarea').forEach(el => {
    if (!visivel(el)) return;
    out.textareas.push({ name: el.name || '', id: el.id || '', label: rotulo(el), placeholder: el.placeholder || '' });
  });
  document.querySelectorAll('button, input[type=submit], a[role=button]').forEach(el => {
    if (!visivel(el)) return;
    const txt = (el.innerText || el.value || '').trim();
    if (txt) out.botoes.push({ texto: txt, id: el.id || '', classe: el.className || '' });
  });
  return out;
}
"""


def extrair_de(contexto, nome):
    try:
        dados = contexto.evaluate(JS_EXTRAIR)
    except Exception as e:
        return None
    total = len(dados["inputs"]) + len(dados["selects"]) + len(dados["textareas"])
    if total == 0:
        return None
    print(f"\n========== FORMULARIO em: {nome} ==========")
    if dados["inputs"]:
        print(f"\n-- INPUTS ({len(dados['inputs'])}) --")
        for c in dados["inputs"]:
            print(f"  [{c['type']}] name='{c['name']}' id='{c['id']}' "
                  f"label='{c['label']}' placeholder='{c['placeholder']}'"
                  f"{' *OBRIGATORIO' if c['required'] else ''}")
    if dados["selects"]:
        print(f"\n-- SELECTS ({len(dados['selects'])}) --")
        for c in dados["selects"]:
            opts = ", ".join(f"{o['text']}({o['value']})" for o in c["options"][:12])
            print(f"  name='{c['name']}' id='{c['id']}' label='{c['label']}'")
            print(f"      opcoes: {opts}")
    if dados["textareas"]:
        print(f"\n-- TEXTAREAS ({len(dados['textareas'])}) --")
        for c in dados["textareas"]:
            print(f"  name='{c['name']}' id='{c['id']}' label='{c['label']}'")
    if dados["botoes"]:
        print(f"\n-- BOTOES ({len(dados['botoes'])}) --")
        for c in dados["botoes"][:25]:
            print(f"  '{c['texto']}' id='{c['id']}'")
    return dados


def main():
    SAIDAS.mkdir(exist_ok=True)
    with abrir_navegador(headless=True) as context:
        page = context.pages[0] if context.pages else context.new_page()
        print(f">> Abrindo: {URL}")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        print(f">> Titulo da pagina: {page.title()}")
        print(f">> URL final:        {page.url}")

        # Rola a pagina toda pra carregar conteudo lazy.
        for _ in range(8):
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(400)
        page.wait_for_timeout(1000)

        resultado = {"url": page.url, "titulo": page.title(), "principal": None, "iframes": []}

        # Formulario na pagina principal.
        resultado["principal"] = extrair_de(page, "pagina principal")

        # Muitas LPs poem o form num iframe (RD Station, etc). Varre os iframes.
        for i, frame in enumerate(page.frames):
            if frame == page.main_frame:
                continue
            d = extrair_de(frame, f"iframe #{i} ({frame.url[:80]})")
            if d:
                resultado["iframes"].append({"url": frame.url, "campos": d})

        # Salva print + html + json.
        page.screenshot(path=str(SAIDAS / "movida_lp.png"), full_page=True)
        (SAIDAS / "movida_lp.html").write_text(page.content(), encoding="utf-8")
        (SAIDAS / "movida_lp_campos.json").write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n>> Print salvo:  saidas/movida_lp.png")
        print(f">> HTML salvo:   saidas/movida_lp.html")
        print(f">> Campos JSON:  saidas/movida_lp_campos.json")


if __name__ == "__main__":
    main()
