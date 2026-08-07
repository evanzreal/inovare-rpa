"""
Movida · Análise de crédito · PARTE 2 — LER O RESULTADO NO PORTAL.

Estratégia: filtra por nome no portal B2B, tira screenshot, usa Gemini Vision
(via OpenRouter) para extrair Status Reserva da tabela.
"""
import base64
import json
import os
import time

import httpx
from dotenv import load_dotenv

from . import config
from ....modelos import ResultadoCredito, STATUS_APROVADO, STATUS_REPROVADO, STATUS_ERRO
from ....util import so_digitos
from ....navegador import RAIZ

load_dotenv(RAIZ / ".env")

SAIDAS = RAIZ / "saidas" / "credito" / "movida"
PORTAL_URL = "https://portalb2b.movida.com.br/relatorios/pedidos"
_OCR_MODEL = "google/gemini-2.5-flash"
_MAPA_STATUS = {
    "aprovada": STATUS_APROVADO,
    "reprovada": STATUS_REPROVADO,
}


# ──────────────────────────────────────────────
# Helpers de navegação
# ──────────────────────────────────────────────

def _aceitar_cookies(page):
    for sel in ["text=Permitir cookies", "text=Aceitar", "text=Dispensar",
                "button:has-text('Permitir')", "#onetrust-accept-btn-handler"]:
        try:
            b = page.locator(sel).first
            if b.is_visible(timeout=1500):
                b.click()
                page.wait_for_timeout(600)
                return
        except Exception:
            pass


def _filtrar_por_nome(page, nome: str) -> bool:
    """Preenche o campo de filtro Nome na tabela."""
    tentativas = [
        lambda: page.get_by_placeholder("Nome"),
        lambda: page.locator("input[placeholder*='ome' i]"),
        lambda: page.locator("mat-form-field input").nth(4),
        lambda: page.locator("input").nth(4),
    ]
    for fn in tentativas:
        try:
            loc = fn()
            if loc.count() and loc.is_visible(timeout=2000):
                loc.fill(nome)
                page.wait_for_timeout(1800)
                return True
        except Exception:
            continue
    return False


# ──────────────────────────────────────────────
# OCR via Gemini Vision (OpenRouter)
# ──────────────────────────────────────────────

def _ocr_screenshot(img_path: str, nome: str | None = None) -> list[dict]:
    """
    Envia screenshot para o Gemini e retorna lista de linhas da tabela:
    [{"pedido_frota": "...", "data_criacao": "...", "status_reserva": "..."}]
    """
    load_dotenv(RAIZ / ".env", override=False)
    api_key = os.getenv("OPENROUTER_TOKEN") or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("   !! OPENROUTER_TOKEN nao encontrada no .env")
        return []

    with open(img_path, "rb") as f:
        img_b64 = base64.standard_b64encode(f.read()).decode()

    prompt = (
        "Esta imagem é uma tabela do portal B2B da Movida. "
        "Extraia TODAS as linhas de dados visíveis (ignore cabeçalhos). "
        "Cada item deve ter: pedido_frota, data_criacao, status_reserva. "
        "IMPORTANTE: retorne TODAS as linhas, não filtre por nada. "
        "Retorne APENAS o JSON array, sem markdown, sem explicação. "
        "Exemplo: [{\"pedido_frota\":\"123\",\"data_criacao\":\"03/08/2026 08:41\",\"status_reserva\":\"Reprovada\"}]"
    )

    payload = {
        "model": _OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": 1024,
    }

    try:
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()
        texto = raw["choices"][0]["message"]["content"].strip()
        # Remove possível ```json ... ```
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        linhas = json.loads(texto)
        print(f"   OCR retornou {len(linhas)} linha(s)")
        for l in linhas:
            print(f"     {l}")
        return linhas
    except Exception as e:
        print(f"   !! OCR erro: {e}")
        return []


# ──────────────────────────────────────────────
# Função principal
# ──────────────────────────────────────────────

def ler_resultado(
    documento: str,
    context,
    nome: str | None = None,
    aguardar_s: int = 20,
    lead_id: str | None = None,
) -> ResultadoCredito:
    """
    Lê o resultado da análise de crédito no portal B2B Movida.

    documento : CPF ou CNPJ
    context   : contexto Playwright já aberto (com sessão logada)
    nome      : nome do cliente para filtrar a tabela
    aguardar_s: segundos de espera antes de abrir o portal
    lead_id   : pedido_frota retornado pela parte1 (para confirmar linha correta)
    """
    res = ResultadoCredito(locadora="movida", documento=so_digitos(documento))
    page = context.new_page()

    try:
        if aguardar_s:
            print(f">> Movida pt2 | aguardando {aguardar_s}s...")
            time.sleep(aguardar_s)

        page.goto(PORTAL_URL, wait_until="networkidle", timeout=60000)
        titulo = page.title()
        print(f"   titulo: {titulo}")

        if "momento" in titulo.lower() or "cloudflare" in titulo.lower():
            res.status = STATUS_ERRO
            res.detalhe = "Cloudflare bloqueando."
            return res

        _aceitar_cookies(page)
        page.wait_for_timeout(1500)

        # Filtra por nome
        if nome:
            filtrou = _filtrar_por_nome(page, nome)
            print(f"   filtro por nome '{nome}': {'ok' if filtrou else 'falhou'}")
            page.wait_for_timeout(1500)

        SAIDAS.mkdir(parents=True, exist_ok=True)
        shot = SAIDAS / f"portal_{so_digitos(documento)}.png"

        # Retry: até 3 tentativas com 25s de espera entre cada
        linhas = []
        for tentativa in range(3):
            if tentativa > 0:
                print(f"   retry {tentativa}/2 — aguardando 25s...")
                time.sleep(25)
                page.reload(wait_until="networkidle", timeout=60000)
                _aceitar_cookies(page)
                page.wait_for_timeout(2000)
                if nome:
                    _filtrar_por_nome(page, nome)
                    page.wait_for_timeout(1800)

            # Scroll para garantir que Angular renderizou a tabela
            page.evaluate("() => window.scrollTo(0, 600)")
            page.wait_for_timeout(1500)

            page.screenshot(path=str(shot), full_page=True)
            res.print_path = str(shot)
            print(f"   screenshot salvo (tentativa {tentativa+1}): {shot}")

            linhas = _ocr_screenshot(str(shot), nome=nome)
            if linhas:
                break

        if not linhas:
            res.status = STATUS_ERRO
            res.detalhe = "OCR nao retornou linhas da tabela (3 tentativas)."
            return res

        # Escolhe a linha correta: por lead_id se disponível, senão a mais recente (primeira)
        linha_alvo = linhas[0]
        if lead_id:
            for l in linhas:
                if str(l.get("pedido_frota", "")).strip() == str(lead_id).strip():
                    linha_alvo = l
                    break

        status_raw = linha_alvo.get("status_reserva", "").strip().lower()
        res.bruto = linha_alvo
        print(f"   linha escolhida: {linha_alvo}")
        print(f"   status_reserva: {status_raw!r}")

        if status_raw in _MAPA_STATUS:
            res.status = _MAPA_STATUS[status_raw]
        else:
            res.status = STATUS_ERRO
            res.detalhe = f"Status nao reconhecido: {status_raw!r}"

    except Exception as e:
        res.status = STATUS_ERRO
        res.detalhe = f"{type(e).__name__}: {e}"
        print(f"   !! ERRO: {res.detalhe}")
    finally:
        try:
            page.close()
        except Exception:
            pass

    return res
