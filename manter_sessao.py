"""
MANTENEDOR DE SESSÃO (keep-alive).

Mantem os portais logados ATIVOS pra a sessao nao cair por inatividade (e nao
pedir token de novo). NAO envia nada, NAO gera proposta/contrato — so cutuca:
abre uma aba por portal, e de tempos em tempos move o mouse, rola a tela e
confere se continua logado. Recarrega de vez em quando pra revalidar.

Guard rails:
  - detecta se caiu pra tela de login / Cloudflare / pediu token -> loga AVISO
    (e escreve em saidas/status_sessao.json pra dar pra monitorar de fora).
  - nunca clica em botoes de acao; so interacoes neutras (mouse/scroll/foco).

Uso:
  python manter_sessao.py                # headed (Mac) — abre janelas
  python manter_sessao.py --headless     # sem janela (so onde nao tem Cloudflare)
  python manter_sessao.py --intervalo 180 --recarregar-a-cada 6

Em servidor Linux (VPS) sem tela, rodar sob Xvfb (ver deploy_vps.sh).
"""

import sys
import json
import time
import argparse
import datetime as dt
from pathlib import Path

from rpa.navegador import abrir_navegador, RAIZ
from rpa.portais import PORTAIS

SAIDAS = RAIZ / "saidas"
STATUS_JSON = SAIDAS / "status_sessao.json"
LOG = SAIDAS / "manter_sessao.log"


def agora() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def registrar(msg: str):
    linha = f"[{agora()}] {msg}"
    print(linha, flush=True)
    try:
        SAIDAS.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def estado_da_pagina(page) -> tuple[str, str]:
    """Devolve (estado, detalhe). estado: 'ok' | 'login' | 'cloudflare' | 'erro'."""
    try:
        url = (page.url or "").lower()
        titulo = (page.title() or "")
        corpo = ""
        try:
            corpo = page.inner_text("body")[:500].lower()
        except Exception:
            pass
        if any(p in titulo.lower() for p in ["momento", "moment"]) or \
           "confirme que" in corpo or "não é um robô" in corpo or "nao e um robo" in corpo:
            return "cloudflare", titulo
        # so considera "login" se tem campo de senha OU se a URL termina num endpoint tipico de auth
        tem_senha = page.locator("input[type=password]").count() > 0
        url_login = any(url.rstrip("/").endswith(p) for p in ["login", "signin", "entrar"]) or \
                    any(p in url for p in ["/login", "/signin", "/sign-in", "?login", "?auth"])
        if tem_senha or url_login:
            return "login", url
        return "ok", titulo
    except Exception as e:
        return "erro", f"{type(e).__name__}: {e}"


def tentar_auto_login(page, seletor_botao: str) -> bool:
    """
    Se o portal mostra modal com credenciais ja preenchidas (ex.: LM Mobilidade),
    clica no botao 'Entrar' automaticamente. Retorna True se clicou.
    """
    try:
        # so clica se o campo de senha JA tiver valor (credenciais salvas no cookie)
        senha = page.locator("input[type=password]").first
        if senha.count() == 0:
            return False
        val = senha.input_value(timeout=1000)
        if not val:
            return False
        botao = page.locator(seletor_botao).first
        if botao.is_visible(timeout=2000):
            botao.click(timeout=5000)
            page.wait_for_timeout(2000)
            return True
    except Exception:
        pass
    return False


def cutucar(page, recarregar: bool, portal: dict):
    """Interacao neutra pra manter a sessao ativa (sem acionar nada de negocio)."""
    try:
        page.bring_to_front()
    except Exception:
        pass
    if recarregar:
        try:
            page.reload(wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
        except Exception:
            pass
    # portais com modal de auto-login (credenciais salvas, so precisa clicar)
    if portal.get("auto_login_botao"):
        clicou = tentar_auto_login(page, portal["auto_login_botao"])
        if clicou:
            registrar(f"[{portal['nome']}] auto-login: clicou 'Entrar' (credenciais salvas)")
    # mexe o mouse e rola um pouco (vai e volta) pra parecer atividade
    try:
        page.mouse.move(400, 300)
        page.mouse.move(700, 450)
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(400)
        page.mouse.wheel(0, -300)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--intervalo", type=int, default=180,
                    help="segundos entre cada rodada de cutucada (padrao 180 = 3min)")
    ap.add_argument("--recarregar-a-cada", type=int, default=8,
                    help="recarrega a pagina a cada N rodadas (padrao 8)")
    ap.add_argument("--headless", action="store_true",
                    help="sem janela (NAO recomendado p/ portais com Cloudflare)")
    args = ap.parse_args()

    registrar(f"=== MANTENEDOR iniciado | intervalo={args.intervalo}s | "
              f"recarrega a cada {args.recarregar_a_cada} rodadas | "
              f"headless={args.headless} | portais={[p['nome'] for p in PORTAIS]} ===")

    with abrir_navegador(headless=args.headless) as context:
        # abre uma aba por portal
        paginas = {}
        primeira = context.pages[0] if context.pages else None
        for i, portal in enumerate(PORTAIS):
            page = primeira if (i == 0 and primeira) else context.new_page()
            try:
                page.goto(portal["url"], wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)
            except Exception as e:
                registrar(f"[{portal['nome']}] erro ao abrir: {e}")
            paginas[portal["nome"]] = page

        rodada = 0
        while True:
            rodada += 1
            recarregar = (rodada % args.recarregar_a_cada == 0)
            resumo = {}
            for portal in PORTAIS:
                nome = portal["nome"]
                page = paginas.get(nome)
                if page is None:
                    continue
                # portais com Cloudflare: evitar recarregar (re-desafia); so interagir
                rec = recarregar and not portal.get("cloudflare")
                cutucar(page, recarregar=rec, portal=portal)
                estado, detalhe = estado_da_pagina(page)
                resumo[nome] = estado
                if estado == "ok":
                    registrar(f"[{nome}] ok")
                else:
                    registrar(f"[{nome}] ⚠️ {estado.upper()} — {detalhe[:80]}")

            # grava status pra monitorar de fora
            try:
                SAIDAS.mkdir(exist_ok=True)
                STATUS_JSON.write_text(json.dumps(
                    {"atualizado": agora(), "rodada": rodada, "status": resumo},
                    ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

            time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
