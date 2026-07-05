# Bootstrap the Social Support AI stack (Windows / PowerShell).
# Run AFTER `docker compose up -d --build`.
#
#   1. Train the scikit-learn models -> ml/artifacts (mounted into backend)
#   2. Pull the local Ollama models (LLM + embeddings)
#   3. Seed the Qdrant enablement knowledge base + Neo4j constraints
#
# Usage:  ./scripts/bootstrap.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==> [1/3] Training ML models (synthetic data + fit)..." -ForegroundColor Cyan
Push-Location (Join-Path $repoRoot "ml")
uv sync
uv run python -m ssa_ml.generate_data
uv run python -m ssa_ml.train
uv run python -m ssa_ml.generate_documents
Pop-Location

Write-Host "==> [2/3] Pulling Ollama models (this can take several minutes)..." -ForegroundColor Cyan
$llm = (docker exec ssa_backend printenv OLLAMA_LLM_MODEL).Trim()
$emb = (docker exec ssa_backend printenv OLLAMA_EMBED_MODEL).Trim()
if (-not $llm) { $llm = "qwen2.5:3b-instruct" }
if (-not $emb) { $emb = "nomic-embed-text" }
docker exec ssa_ollama ollama pull $llm
docker exec ssa_ollama ollama pull $emb

Write-Host "==> [3/3] Seeding knowledge base (Qdrant) + Neo4j constraints..." -ForegroundColor Cyan
docker exec ssa_backend uv run --no-dev python -m app.scripts.seed_kb

Write-Host "==> Bootstrap complete. UI: http://localhost:8501  API docs: http://localhost:8000/docs" -ForegroundColor Green
