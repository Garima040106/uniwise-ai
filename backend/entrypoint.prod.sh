#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec uvicorn uniwise.asgi:application \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${UVICORN_WORKERS:-2}" \
  --proxy-headers
