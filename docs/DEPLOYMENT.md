# Deployment Guide

## One-command production deploy

From repo root:

```bash
./deploy_prod.sh
```

This command will:
- create `.env.prod` from `.env.prod.example` if missing
- generate a random `SECRET_KEY` automatically
- build and start the production stack (`db`, `backend`, `web`)
- build backend with `requirements.prod.txt` (lean production dependency set)

## Stack components

- `db`: PostgreSQL 15
- `backend`: Django + Uvicorn (`/app/entrypoint.prod.sh`)
- `web`: Nginx serving React build and proxying `/api` and `/admin`

## URLs

- App: `http://localhost` (or `http://localhost:<WEB_PORT>`)
- API (proxied): `http://localhost/api/...`
- Admin (proxied): `http://localhost/admin/`

## Useful commands

```bash
# Check running services
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

# Tail logs
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f

# Restart stack
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build

# Stop stack
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

## Required production edits in `.env.prod`

Before exposing publicly, update:
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_SSL_REDIRECT=True` (if TLS termination is configured)
- `OLLAMA_BASE_URL` to reachable Ollama endpoint
