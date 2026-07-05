#!/usr/bin/env bash
# Bootstrap the Social Support AI stack (Linux / macOS).
# Run AFTER `docker compose up -d --build`.
#
#   1. Train the scikit-learn models -> ml/artifacts (mounted into backend)
#   2. Pull the local Ollama models (LLM + embeddings)
#   3. Seed the Qdrant enablement knowledge base + Neo4j constraints
#
# Usage:  ./scripts/bootstrap.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> [1/3] Training ML models (synthetic data + fit)..."
pushd "$REPO_ROOT/ml" >/dev/null
uv sync
uv run python -m ssa_ml.generate_data
uv run python -m ssa_ml.train
uv run python -m ssa_ml.generate_documents
popd >/dev/null

echo "==> [2/3] Pulling Ollama models (this can take several minutes)..."
LLM="$(docker exec ssa_backend printenv OLLAMA_LLM_MODEL 2>/dev/null || echo qwen2.5:3b-instruct)"
EMB="$(docker exec ssa_backend printenv OLLAMA_EMBED_MODEL 2>/dev/null || echo nomic-embed-text)"
docker exec ssa_ollama ollama pull "$LLM"
docker exec ssa_ollama ollama pull "$EMB"

echo "==> [3/3] Seeding knowledge base (Qdrant) + Neo4j constraints..."
docker exec ssa_backend uv run --no-dev python -m app.scripts.seed_kb

echo "==> Bootstrap complete. UI: http://localhost:8501  API docs: http://localhost:8000/docs"
