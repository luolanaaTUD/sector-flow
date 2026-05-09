#!/usr/bin/env sh
set -eu

echo "Waiting for database at db:5432..."
until python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('db', 5432)); s.close()"; do
  sleep 1
done

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting API server..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
