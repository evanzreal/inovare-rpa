"""
Gestao do navegador controlado pelo RPA.

Usamos um "perfil persistente": o Chromium guarda cookies/login numa pasta
(.perfil_chrome/). Voce loga UMA vez nas locadoras nesse navegador e, a partir
dai, todos os scripts reusam a mesma sessao logada.

No VPS Linux, o /etc/ld.so.preload injeta libgcwrap.so em todos os processos,
o que trava o Chrome durante a inicializacao. A funcao _abrir_vps contorna isso
lancando o Chrome em um mount namespace proprio via `unshare --mount`.
"""

import sys
import glob
import subprocess
import time
from pathlib import Path
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
PERFIL = RAIZ / ".perfil_chrome"

_CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--password-store=basic",
]


def _encontrar_chromium() -> str:
    import playwright
    # Tenta primeiro na pasta do pacote (instalacao padrão)
    base = Path(playwright.__file__).parent / "driver" / "package" / ".local-browsers"
    candidatos = list(base.glob("chromium-*/chrome-linux/chrome"))
    if candidatos:
        return str(sorted(candidatos)[-1])
    # Fallback: cache global do Playwright (~/.cache/ms-playwright)
    cache = Path.home() / ".cache" / "ms-playwright"
    candidatos = list(cache.glob("chromium-*/chrome-linux/chrome"))
    if candidatos:
        return str(sorted(candidatos)[-1])
    raise FileNotFoundError("Chromium do Playwright nao encontrado")


def _limpar_locks():
    for padrao in [
        str(PERFIL / "Singleton*"),
        str(PERFIL / "Default" / "LOCK"),
        str(PERFIL / "RunningChromeVersion"),
    ]:
        for f in glob.glob(padrao):
            try:
                Path(f).unlink()
            except OSError:
                pass


@contextmanager
def _abrir_vps(headless: bool, slow_mo: int):
    """
    Lanca o Chrome em um mount namespace isolado para evitar que o
    /etc/ld.so.preload do VPS injete libgcwrap.so, que trava o Chrome.
    Conecta via CDP (remote-debugging-port) em vez de pipe.
    """
    PERFIL.mkdir(exist_ok=True)
    _limpar_locks()

    chrome = _encontrar_chromium()
    port = 9301

    chrome_args = " ".join(_CHROME_ARGS)
    headless_flag = "--headless=new" if headless else ""
    display_export = "" if headless else "export DISPLAY=:1 &&"

    cmd = (
        f"{display_export} exec {chrome} "
        f"{chrome_args} --disable-gpu "
        f"--user-data-dir={PERFIL} "
        f"--remote-debugging-port={port} "
        f"{headless_flag} about:blank"
    )

    proc = subprocess.Popen(
        ["unshare", "--mount", "--", "bash", "-c",
         f"mount --bind /dev/null /etc/ld.so.preload && {cmd}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        time.sleep(5)
        if proc.poll() is not None:
            raise RuntimeError(f"Chrome encerrou antes de conectar (rc={proc.returncode})")

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            if slow_mo:
                context.set_default_timeout(slow_mo * 100)
            try:
                yield context
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    finally:
        proc.kill()
        proc.wait()


@contextmanager
def _abrir_mac(headless: bool, slow_mo: int):
    """
    Lanca o Chrome via Playwright nativo (Mac / sistemas sem preload problem).
    """
    PERFIL.mkdir(exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PERFIL),
            headless=headless,
            slow_mo=slow_mo,
            viewport={"width": 1440, "height": 900},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            args=_CHROME_ARGS,
        )
        try:
            yield context
        finally:
            context.close()


@contextmanager
def abrir_navegador(headless: bool = False, slow_mo: int = 0):
    """
    Abre o navegador com o perfil persistente e devolve o 'context'.

    headless=False  -> janela visivel (use pra logar e pra desenvolver/ver o robo).
    headless=True   -> sem janela (use em producao, rodando sozinho).
    slow_mo         -> ms de pausa entre acoes, ajuda a "ver" o robo agindo.
    """
    if sys.platform == "linux":
        with _abrir_vps(headless=headless, slow_mo=slow_mo) as ctx:
            yield ctx
    else:
        with _abrir_mac(headless=headless, slow_mo=slow_mo) as ctx:
            yield ctx
