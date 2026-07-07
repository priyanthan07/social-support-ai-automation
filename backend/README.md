# Social Support AI - Backend

FastAPI service exposing the application intake, document upload, processing,
status/decision, and chat endpoints. The AI workflow is implemented as a
LangGraph supervisor graph (extraction -> validation -> eligibility ->
recommendation) with local Ollama LLMs, a scikit-learn decision model, and
Langfuse observability.

See the repository root `README.md` for full run instructions.
