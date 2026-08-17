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
from rpa.fluxos.analise_credito.b2e.pesquisa import buscar as b2e_buscar
from rpa.fluxos.analise_credito.localiza.caminho import Localiza as LocalizaCaminho
from rpa.modelos import Cliente

_localiza = LocalizaCaminho()

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


def _abrir_portais():
    """Navega para a Localiza na aba inicial para o usuário fazer login."""
    if not _context:
        return
    try:
        page = _context.pages[0]
        page.goto(
            "https://localiza.my.site.com/meoorevendas/s/",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        print(">> Browser na Localiza — faça login para começar.")
    except Exception as e:
        print(f">> Aviso: navegação inicial para Localiza falhou: {e}")


async def _keepalive_localiza():
    """Clica na aba Localiza a cada 60s para manter a sessão ativa."""
    while True:
        await asyncio.sleep(60)
        if not _context:
            continue
        def _click():
            for page in _context.pages:
                if "localiza" in page.url.lower():
                    try:
                        page.mouse.move(400, 300)
                        page.mouse.click(400, 300)
                    except Exception:
                        pass
                    return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, _click)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _abrir_browser)
    await loop.run_in_executor(_executor, _abrir_portais)
    asyncio.create_task(_keepalive_localiza())
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


@app.get("/debug/b2e/{cpf}")
async def debug_b2e(cpf: str):
    """Busca CPF no portal B2E e retorna screenshot + texto completo da página."""
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")

    def _buscar():
        import base64
        from rpa.util import so_digitos
        cpf_limpo = so_digitos(cpf)
        page = _context.new_page()
        try:
            # Navega diretamente com CPF na querystring (form é GET server-side)
            url = f"https://webantifraudes.b2egroup.com.br/Web/Pesquisa?IDENTIFICADOR={cpf_limpo}"
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(1500)

            shot = "/tmp/b2e_resultado.png"
            page.screenshot(path=shot, full_page=True)

            # Lê tabela diretamente do DOM (HTML server-rendered, não Angular)
            linhas = page.evaluate("""() => {
                const rows = [...document.querySelectorAll('table tbody tr')];
                return rows.map(tr => ({
                    colunas: [...tr.querySelectorAll('td')].map(td => td.innerText.trim())
                }));
            }""")

            img_b64 = base64.standard_b64encode(open(shot, "rb").read()).decode()
            return {
                "cpf_buscado": cpf_limpo,
                "url_usada": url,
                "linhas": linhas,
                "screenshot_b64": img_b64,
            }
        finally:
            page.close()

    async with _lock:
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(_executor, _buscar)

    # Salva screenshot localmente para visualização
    import base64
    shot_path = "/tmp/b2e_resultado.png"
    with open(shot_path, "wb") as f:
        f.write(base64.standard_b64decode(resultado.pop("screenshot_b64")))
    resultado["screenshot"] = shot_path
    return resultado


@app.get("/debug/navegar")
async def debug_navegar(url: str):
    """Abre URL na primeira aba do browser."""
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")
    def _nav():
        page = _context.pages[0] if _context.pages else _context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        return {"url": page.url, "titulo": page.title()}
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _nav)


@app.get("/debug/b2e-login")
async def debug_b2e_login():
    """Clica em Entrar/Login no portal B2E."""
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")
    def _login():
        import base64
        page = _context.pages[0]
        page.wait_for_timeout(1000)

        # Tira screenshot antes para diagnóstico
        shot_antes = "/tmp/b2e_antes_login.png"
        page.screenshot(path=shot_antes)

        # Lista todos botões e links visíveis
        elementos = page.evaluate("""() =>
            [...document.querySelectorAll('button, a, input[type=submit], input[type=button]')]
            .filter(e => e.offsetParent !== null)
            .map(e => ({ tag: e.tagName, text: e.innerText || e.value, href: e.href || '', id: e.id }))
        """)

        # Tenta clicar em qualquer coisa que pareça login/entrar
        clicou = False
        for tentativa in [
            lambda: page.get_by_role("button", name="Entrar").click(timeout=5000),
            lambda: page.get_by_role("button", name="Login").click(timeout=5000),
            lambda: page.get_by_text("Entrar").click(timeout=5000),
            lambda: page.locator("input[type=submit]").click(timeout=5000),
            lambda: page.locator("button").first.click(timeout=5000),
        ]:
            try:
                tentativa()
                clicou = True
                break
            except Exception:
                pass

        page.wait_for_timeout(4000)
        shot_depois = "/tmp/b2e_depois_login.png"
        page.screenshot(path=shot_depois)

        return {
            "url": page.url,
            "titulo": page.title(),
            "clicou": clicou,
            "elementos_visiveis": elementos[:20],
        }
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _login)


@app.get("/debug/tabs")
async def debug_tabs():
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")
    def _listar():
        return [{"index": i, "url": p.url, "titulo": p.title()} for i, p in enumerate(_context.pages)]
    loop = asyncio.get_event_loop()
    tabs = await loop.run_in_executor(_executor, _listar)
    return {"tabs": tabs}


@app.get("/debug/ver")
async def debug_ver(aba: int = 0):
    """
    Tira screenshot da aba indicada (padrão: primeira) e retorna como imagem PNG.
    Use para compartilhar o estado atual do browser.
    """
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")
    import base64
    from fastapi.responses import Response
    def _shot():
        pages = _context.pages
        if not pages:
            raise Exception("Nenhuma aba aberta")
        page = pages[min(aba, len(pages) - 1)]
        path = f"/tmp/ver_aba{aba}.png"
        page.screenshot(path=path, full_page=False)
        with open(path, "rb") as f:
            return f.read()
    loop = asyncio.get_event_loop()
    img = await loop.run_in_executor(_executor, _shot)
    return Response(content=img, media_type="image/png")


@app.post("/credito/b2e")
async def credito_b2e(req: ResultadoRequest):
    """Busca CPF no portal antifraude B2E e retorna o status mais recente."""
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")
    async with _lock:
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            _executor,
            lambda: b2e_buscar(cpf=req.documento, context=_context),
        )
    return asdict(resultado)


class LocalizaRequest(BaseModel):
    nome: str
    documento: str


class PipelineRequest(BaseModel):
    documento: str                # CPF ou CNPJ
    nome: str = "Cliente"         # nome para a Movida (qualquer valor serve)
    aguardar_movida_s: int = 40  # tempo de espera antes de ler resultado Movida


@app.post("/credito/localiza")
async def credito_localiza(req: LocalizaRequest):
    """Cria lead no Localiza Meoo Revendas e lê o resultado da pré-análise."""
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")
    async with _lock:
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            _executor,
            lambda: _localiza.consultar(
                Cliente(nome=req.nome, documento=req.documento),
                _context,
            ),
        )
    return asdict(resultado)


@app.post("/credito/pipeline")
async def credito_pipeline(req: PipelineRequest):
    """
    Pipeline completo de análise de crédito.

    Sequência:
    1. B2E antifraude  (~5s)
    2. Movida parte 1  — cria lead (~10s)
    3. Movida parte 2  — lê portal B2B (~40s + OCR)
    4. Localiza        — cria lead + pré-análise (~25s)

    Retorna: {cliente, b2e, movida_envio, movida_resultado, localiza}
    """
    if not _context:
        raise HTTPException(503, detail="Browser nao inicializado")

    async with _lock:
        loop = asyncio.get_event_loop()
        import json as _json

        nome = req.nome

        # 1. Movida parte1 — envia lead (cria o registro na Movida e dispara análise B2E)
        envio = await loop.run_in_executor(
            _executor,
            lambda: enviar_lead(
                nome=nome,
                cpf=req.documento,
                telefone=movida_config.TELEFONE,
                regiao=None,
                cod_vendedor=movida_config.COD_VENDEDOR,
                enviar=True,
                context=_context,
                salvar_print=True,
            ),
        )

        # Extrai lead_id do JSON de resposta
        lead_id = None
        try:
            lead_id = str(_json.loads(envio.resposta).get("leadId", ""))
        except Exception:
            pass

        # 2. B2E — lê resultado antifraude gerado pela Movida
        b2e_res = await loop.run_in_executor(
            _executor,
            lambda: b2e_buscar(cpf=req.documento, context=_context),
        )

        # 3. Movida parte2 — lê resultado do portal B2B (com retry interno)
        movida_res = await loop.run_in_executor(
            _executor,
            lambda: ler_resultado(
                documento=req.documento,
                context=_context,
                nome=nome,
                aguardar_s=req.aguardar_movida_s,
                lead_id=lead_id,
            ),
        )

        # 4. Localiza
        localiza_res = await loop.run_in_executor(
            _executor,
            lambda: _localiza.consultar(
                Cliente(documento=req.documento, nome=nome),
                _context,
            ),
        )

    return {
        "cliente":          {"nome": nome, "documento": req.documento},
        "b2e":              asdict(b2e_res),
        "movida_envio":     asdict(envio),
        "movida_resultado": asdict(movida_res),
        "localiza":         asdict(localiza_res),
    }


@app.post("/credito/movida")
async def credito_movida(req: CreditoRequest):
    """
    Parte 1: preenche o formulario de analise de credito na Movida.
    - enviar=false (padrao): dry-run, nao submete o lead.
    - enviar=true: cria o lead de verdade.
    - ler_resultado=true: apos enviar, aguarda ~20s e le o Status Reserva no portal (requer login B2B) e consulta o B2E.
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
            lead_id = None
            try:
                import json as _json
                lead_id = str(_json.loads(envio.resposta).get("leadId", ""))
            except Exception:
                pass

            credito_movida_res = await loop.run_in_executor(
                _executor,
                lambda: ler_resultado(
                    documento=req.cpf,
                    context=_context,
                    nome=req.nome,
                    aguardar_s=20,
                    lead_id=lead_id,
                ),
            )

            credito_b2e_res = await loop.run_in_executor(
                _executor,
                lambda: b2e_buscar(cpf=req.documento, context=_context),
            )

            return {
                "envio": asdict(envio),
                "movida": asdict(credito_movida_res),
                "b2e": asdict(credito_b2e_res),
            }

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
