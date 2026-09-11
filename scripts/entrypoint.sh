#!/bin/sh
# entrypoint.sh — Run Alembic migrations then start the server.
# Using 'sh' (not bash) for maximum compatibility with slim base images.
set -e

echo ">>> Running database migrations..."
alembic upgrade head

echo ">>> Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
