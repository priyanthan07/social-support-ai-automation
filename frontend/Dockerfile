# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501

ENTRYPOINT ["uv", "run", "streamlit", "run", "ssa_frontend/app.py", \
    "--server.port=8501", "--server.address=0.0.0.0", \
    "--server.headless=true", "--browser.gatherUsageStats=false"]
