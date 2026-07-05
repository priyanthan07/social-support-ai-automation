#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Applying database migrations (alembic upgrade head)..."
uv run --no-dev alembic upgrade head

echo "[entrypoint] Starting FastAPI (uvicorn)..."
# Single worker: the in-process LLM concurrency guard assumes one process.
exec uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
