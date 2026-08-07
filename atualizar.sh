#!/bin/bash
# Atualiza o RPA Inovare e reinicia o servidor.
#
# Uso (no Mac do cliente):
#   bash ~/inovare-rpa/atualizar.sh
#
# O que faz:
#   1. git pull (pega código novo do GitHub)
#   2. Reinicia o servidor via LaunchAgent
#   3. Browser abre automaticamente na Localiza — faça login UMA vez
#   4. Servidor fica rodando 24/7 com sessão viva

set -e

cd ~/inovare-rpa

echo ""
echo "=== Inovare RPA — Atualização ==="
echo ""

echo "[1/3] Puxando atualizações do GitHub..."
git pull

echo ""
echo "[2/3] Instalando dependências novas..."
.venv/bin/pip install -r requirements.txt -q

echo ""
echo "[3/3] Reiniciando servidor..."
launchctl kickstart -k "gui/$(id -u)/inovare.rpa"

echo ""
echo "✅ Pronto!"
echo ""
echo "   O browser vai abrir em alguns segundos na Localiza."
echo "   Faça login UMA vez — a sessão fica viva automaticamente."
echo ""
echo "   API: http://localhost:8000"
echo "   Pipeline completo: POST http://localhost:8000/credito/pipeline"
echo "   Logs: tail -f ~/inovare-rpa/logs/server.log"
echo ""
