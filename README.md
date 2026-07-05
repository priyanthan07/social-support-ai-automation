# Social Support Application Workflow Automation

An AI prototype that automates social-support eligibility decisions for a
government social security department. Applicants submit an interactive form
plus documents (Emirates ID, bank statement, resume, assets/liabilities Excel,
credit report); a **LangGraph** multi-agent workflow extracts, validates,
scores (with a local **scikit-learn** model), and recommends a decision plus
economic-enablement options -- in minutes, fully locally hosted, with
end-to-end **Langfuse** observability.

> Full setup, architecture, and design documentation are completed in the
> documentation phase. See `docs/SOLUTION_SUMMARY.md`.

## Quick start (summary)

```bash
# 1. Configure environment
cp .env.example .env
cp .env.dev.example .env.dev        # paste your Langfuse keys here

# 2. Launch the full local stack
docker compose up -d --build

# 3. Train models, pull local LLMs, seed the knowledge base
./scripts/bootstrap.ps1             # Windows
./scripts/bootstrap.sh              # Linux / macOS

# 4. Open the UI
#    http://localhost:8501   (Streamlit)
#    http://localhost:8000/docs  (API)
```

## Tech stack

Python - FastAPI - Streamlit - LangGraph - Ollama - scikit-learn - Langfuse -
PostgreSQL - MongoDB - Qdrant - Neo4j - uv - Alembic - pytest.
