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


@app.get("/status")
async def status():
    return {"browser": "online" if _context else "offline"}


@app.post("/credito/movida")
async def credito_movida(req: CreditoRequest):
    """
    Envia o lead de analise de credito na Movida (parte 1).
    Por padrao roda em dry-run (enviar=false). Passe enviar=true para criar o lead de verdade.
    """
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")

    async with _lock:
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
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

    return asdict(resultado)
