#!/usr/bin/env bash
# Bootstrap the Social Support AI stack (Linux / macOS).
# Run AFTER `docker compose up -d --build` and the README ML training step.
#
#   1. Pull the local Ollama models (LLM + embeddings)
#   2. Seed the Qdrant enablement knowledge base + Neo4j constraints
#
# Usage:  ./scripts/bootstrap.sh
set -euo pipefail

echo "==> [1/2] Pulling Ollama models (this can take several minutes)..."
LLM="$(docker exec ssa_backend printenv OLLAMA_LLM_MODEL 2>/dev/null || echo qwen2.5:3b-instruct)"
EMB="$(docker exec ssa_backend printenv OLLAMA_EMBED_MODEL 2>/dev/null || echo nomic-embed-text)"
docker exec ssa_ollama ollama pull "$LLM"
docker exec ssa_ollama ollama pull "$EMB"

echo "==> [2/2] Seeding knowledge base (Qdrant) + Neo4j constraints..."
docker exec ssa_backend uv run --no-dev python -m app.scripts.seed_kb

echo "==> Bootstrap complete. UI: http://localhost:8501  API docs: http://localhost:8000/docs"
