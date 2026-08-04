#!/bin/bash
# Inicia o túnel Cloudflare para expor a API publicamente.
exec /usr/local/bin/cloudflared tunnel --url http://localhost:8000
