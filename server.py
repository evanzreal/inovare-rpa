"""
Servidor FastAPI — RPA Inovare.

O browser abre uma vez na inicializacao e fica vivo ate o servidor parar.
Um lock garante que apenas uma requisicao usa o browser por vez.

Rodar:
  source .venv/bin/activate
  uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from rpa.navegador import PERFIL, _CHROME_ARGS
from rpa.fluxos.analise_credito.movida.parte1_envio import enviar_lead
from rpa.fluxos.analise_credito.movida.parte2_resultado import ler_resultado
from rpa.fluxos.analise_credito.movida import config as movida_config

_context = None
_playwright = None
_lock = asyncio.Lock()
_executor = ThreadPoolExecutor(max_workers=1)


def _abrir_browser():
    global _context, _playwright
    from playwright.sync_api import sync_playwright
    PERFIL.mkdir(exist_ok=True)
    _playwright = sync_playwright().start()
    _context = _playwright.chromium.launch_persistent_context(
        user_data_dir=str(PERFIL),
        headless=False,
        viewport={"width": 1440, "height": 900},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        args=_CHROME_ARGS,
    )


def _fechar_browser():
    global _context, _playwright
    if _context:
        _context.close()
    if _playwright:
        _playwright.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _abrir_browser)
    yield
    await loop.run_in_executor(_executor, _fechar_browser)


app = FastAPI(title="Inovare RPA", version="0.1.0", lifespan=lifespan)


class CreditoRequest(BaseModel):
    nome: str
    cpf: str
    telefone: str = movida_config.TELEFONE
    regiao: str | None = None
    cod_vendedor: str = movida_config.COD_VENDEDOR
    enviar: bool = False
    ler_resultado: bool = False


class ResultadoRequest(BaseModel):
    cpf: str
    nome: str | None = None
    aguardar_s: int = 0


@app.get("/status")
async def status():
    return {"browser": "online" if _context else "offline"}


@app.post("/credito/movida")
async def credito_movida(req: CreditoRequest):
    """
    Parte 1: preenche o formulario de analise de credito na Movida.
    - enviar=false (padrao): dry-run, nao submete o lead.
    - enviar=true: cria o lead de verdade.
    - ler_resultado=true: apos enviar, aguarda ~20s e le o Status Reserva no portal (requer login B2B).
    """
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")

    async with _lock:
        loop = asyncio.get_event_loop()
        envio = await loop.run_in_executor(
            _executor,
            lambda: enviar_lead(
                nome=req.nome,
                cpf=req.cpf,
                telefone=req.telefone,
                regiao=req.regiao,
                cod_vendedor=req.cod_vendedor,
                enviar=req.enviar,
                context=_context,
                salvar_print=True,
            ),
        )

        if req.ler_resultado and req.enviar:
            credito = await loop.run_in_executor(
                _executor,
                lambda: ler_resultado(
                    documento=req.cpf,
                    context=_context,
                    nome=req.nome,
                    aguardar_s=20,
                ),
            )
            return {"envio": asdict(envio), "credito": asdict(credito)}

    return asdict(envio)


@app.get("/debug/portal")
async def debug_portal():
    """Abre o portal B2B e retorna titulo + texto da pagina para diagnostico."""
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")

    def _inspecionar():
        from rpa.fluxos.analise_credito.movida.parte2_resultado import _aceitar_cookies
        page = _context.new_page()
        try:
            page.goto("https://portalb2b.movida.com.br/relatorios/pedidos",
                      wait_until="networkidle", timeout=60000)
            # Tenta dispensar o banner de cookies de todas as formas
            for sel in ["text=Permitir cookies", "text=Dispensar",
                        "button:has-text('Permitir')", "button:has-text('Aceitar')"]:
                try:
                    page.locator(sel).first.click(timeout=2000)
                    page.wait_for_timeout(800)
                    break
                except Exception:
                    pass
            page.wait_for_timeout(4000)
            # Força scroll para ativar renderização do Angular
            page.evaluate("() => window.scrollTo(0, 800)")
            page.wait_for_timeout(2000)
            titulo = page.title()
            texto = page.evaluate("() => document.body.innerText").strip()
            sh = page.evaluate("() => document.body.scrollHeight")
            inputs_info = page.evaluate("""() =>
                [...document.querySelectorAll('input')].map(e => ({
                    placeholder: e.placeholder, id: e.id, name: e.name
                }))
            """)
            mat_rows = page.locator("mat-row, tr, [role='row']").count()
            page.screenshot(path="/tmp/portal_debug.png", full_page=True)
            return {
                "titulo": titulo,
                "scroll_height": sh,
                "mat_rows": mat_rows,
                "texto_3000": texto[:3000],
                "n_inputs": len(inputs_info),
                "inputs": inputs_info,
            }
        finally:
            page.close()

    async with _lock:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(_executor, _inspecionar)
    return info


@app.post("/credito/movida/resultado")
async def credito_movida_resultado(req: ResultadoRequest):
    """
    Parte 2: le o Status Reserva no portal B2B (Aprovada/Reprovada).
    Util para consultar um resultado ja enviado anteriormente.
    """
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")

    async with _lock:
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            _executor,
            lambda: ler_resultado(
                documento=req.cpf,
                context=_context,
                nome=req.nome,
                aguardar_s=req.aguardar_s,
            ),
        )

    return asdict(resultado)
