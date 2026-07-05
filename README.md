# Social Support Application Workflow Automation

An AI prototype that automates social-support eligibility decisions for a government social security department. Applicants submit an interactive form plus documents (Emirates ID, bank statement, resume, assets/liabilities Excel, credit report); a **LangGraph** multi-agent workflow extracts, validates, scores (with a local **scikit-learn** model), and recommends a decision plus economic-enablement options — in minutes, fully locally hosted, with end-to-end **Langfuse** observability.

## Architecture (high level)

```
Streamlit UI  →  FastAPI  →  LangGraph (Extraction → Validation → Eligibility → Recommendation)
                     ↓              ↓
              PostgreSQL      MongoDB / Qdrant / Neo4j
                     ↓
              scikit-learn (decision) + Ollama (LLM/embeddings)
                     ↓
                 Langfuse traces
```

## Prerequisites

- **Docker Desktop** (with Compose v2)
- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)** (for local ML training and tests)
- **Langfuse Cloud** API keys (optional but recommended for observability)

## Quick start

### 1. Configure environment

```powershell
cd f:\projects\social-support-ai-automation
copy .env.example .env
copy .env.dev.example .env.dev
```

Edit `.env.dev` and paste your Langfuse keys:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

### 2. Train ML models (host machine)

```powershell
cd ml
uv sync
uv run python -m ssa_ml.generate_data
uv run python -m ssa_ml.train
uv run python -m ssa_ml.generate_documents
```

Artifacts are written to `ml/artifacts/` and mounted read-only into the backend container.

### 3. Start the stack

```powershell
cd ..
docker compose up -d --build
```

### 4. Bootstrap Ollama models + knowledge base

Run this **after** step 2 (ML training) and step 3 (Docker stack). It pulls Ollama models and seeds the Qdrant knowledge base — it does **not** re-run ML training.

```powershell
.\scripts\bootstrap.ps1
```

This pulls the local LLM and embedding models into Ollama and seeds the Qdrant enablement knowledge base.

**Note:** The validation agent uses a ReAct tool-calling loop with Ollama. The default `qwen2.5:3b-instruct` model should support native tool calls; if tool execution fails in your environment, try a larger tool-capable instruct model.

**Policy:** Only **Emirates ID** is mandatory for an automatic eligibility decision (`MIN_REQUIRED_DOCS`). Other documents improve accuracy but missing uploads may route the case to manual review rather than auto-decline.

### 5. Open the application

| Service | URL |
|---------|-----|
| **Streamlit UI** | http://localhost:8501 |
| **API docs** | http://localhost:8000/docs |
| **Neo4j Browser** | http://localhost:7474 |
| **Qdrant** | http://localhost:6333 |

## Demo workflow

1. Go to **Apply** in the Streamlit UI.
2. Optionally click **Load demo (Aisha — eligible persona + files)** to pre-fill the form and load any generated demo documents from `data/synthetic/documents/aisha_eligible/`.
3. Fill the form (including household members), upload documents, and click **Submit Application** — processing starts in the background.
4. Open **Live Processing** to watch status transitions (`received → extracting → validating → scoring → recommending → decided`).
5. View the **Decision** page for approve/soft-decline, support amount, and enablement recommendations.
6. Use **Assistant** to ask grounded questions about the case.
7. **Officer Dashboard** lists all applications.

## Project structure

```
backend/     FastAPI + LangGraph agents + extractors + ML runtime
frontend/    Custom Streamlit UI
ml/          Offline synthetic data + scikit-learn training
data/        Knowledge base + synthetic demo documents
scripts/     bootstrap.ps1 / bootstrap.sh
docs/        Solution summary (design document)
```

## Development

### Backend tests

```powershell
cd backend
uv sync --group dev
uv run pytest
```

### ML tests

```powershell
cd ml
uv sync --group dev
uv run pytest
```

### Database migrations

Migrations run automatically on backend startup (`alembic upgrade head`). To create a new migration after model changes:

```powershell
cd backend
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## Tech stack

Python · uv · FastAPI · Streamlit · LangGraph · Ollama · scikit-learn · Langfuse · PostgreSQL · MongoDB · Qdrant · Neo4j · Alembic · pytest

## Documentation

See [`docs/SOLUTION_SUMMARY.md`](docs/SOLUTION_SUMMARY.md) for the full solution design, tool justifications, model card, and future improvements.
