#!/bin/sh
set -eu

if [ "${AUTO_CREATE_SCHEMA:-true}" = "false" ]; then
  echo "Running Alembic migrations..."
  alembic -c alembic.ini upgrade head
fi

echo "Starting FastAPI service..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
