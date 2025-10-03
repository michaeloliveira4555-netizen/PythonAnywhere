#!/usr/bin/env bash
set -euo pipefail

# Script simples para copiar .env.example -> .env no servidor de produção
# e lembrar o operador de preencher variáveis sensíveis.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  echo "Arquivo .env já existe — operação cancelada. Verifique o arquivo existente antes de sobrescrever."
  exit 0
fi

if [ ! -f .env.example ]; then
  echo ".env.example não encontrado. Execute este script a partir da raiz do repositório." >&2
  exit 1
fi

cp .env.example .env
chmod 600 .env || true

cat <<'EOF'
.env criado a partir de .env.example.
Preencha os valores sensíveis em .env (SECRET_KEY, SUPER_ADMIN_PASSWORD, etc.) e não envie este arquivo para o controle de versão.
Verifique também DATABASE_URL e REDIS_URL conforme seu ambiente.
EOF

exit 0
