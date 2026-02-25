#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".env.prod" ]; then
  cp .env.prod.example .env.prod
  if command -v python3 >/dev/null 2>&1; then
    RANDOM_PART="$(python3 - <<'PY'
import secrets
import string

alphabet = string.ascii_letters + string.digits
print("".join(secrets.choice(alphabet) for _ in range(64)))
PY
)"
  else
    RANDOM_PART="$(head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c 1-64)"
  fi
  GENERATED_SECRET="django-insecure-${RANDOM_PART}"
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${GENERATED_SECRET}|" .env.prod
  echo "Created .env.prod from .env.prod.example."
  echo "Review .env.prod (domain, TLS flags, Ollama URL) before internet exposure."
fi

if grep -q "^SECRET_KEY=change-this-secret-key$" .env.prod; then
  echo "Please set a real SECRET_KEY in .env.prod before deploying."
  exit 1
fi

docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

WEB_PORT_VALUE="$(awk -F= '/^WEB_PORT=/{print $2}' .env.prod | tail -n 1)"
if [ -z "${WEB_PORT_VALUE}" ]; then
  WEB_PORT_VALUE="80"
fi

echo "Deployment complete."
echo "Open: http://localhost:${WEB_PORT_VALUE}"
