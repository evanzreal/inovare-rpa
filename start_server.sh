#!/bin/bash
# Inicia o servidor RPA Inovare.
# Chamado pelo LaunchAgent — não editar o caminho abaixo.
cd "$(dirname "$0")"
exec .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
