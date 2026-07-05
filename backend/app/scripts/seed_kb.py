"""Seed the Qdrant enablement knowledge base and create Neo4j constraints.

Run inside the backend container:
    uv run --no-dev python -m app.scripts.seed_kb
"""

from __future__ import annotations

import json
from pathlib import Path

from qdrant_client.models import PointStruct

from app.core.config import settings
from app.core.logging import get_logger
from app.db import neo4j, qdrant
from app.llm import client as llm

logger = get_logger(__name__)


def _load_programs() -> list[dict]:
    path = Path(settings.knowledge_base_path)
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _program_text(program: dict) -> str:
    return (
        f"{program['title']} (category: {program['category']}). "
        f"{program['description']} "
        f"Best for: {program.get('target', '')}. "
        f"Provider: {program.get('provider', '')}."
    )


def seed_qdrant() -> int:
    programs = _load_programs()
    texts = [_program_text(p) for p in programs]
    logger.info("Embedding %d enablement programs via Ollama...", len(texts))
    vectors = llm.embed_documents(texts)

    qdrant.ensure_collection(vector_size=len(vectors[0]))
    points = [
        PointStruct(id=idx, vector=vec, payload={**prog, "text": text})
        for idx, (prog, text, vec) in enumerate(zip(programs, texts, vectors))
    ]
    qdrant.upsert_points(points)
    logger.info("Upserted %d points into Qdrant collection '%s'.", len(points), settings.qdrant_collection)
    return len(points)


def seed_neo4j() -> None:
    neo4j.create_constraints()
    logger.info("Neo4j constraints ensured.")


def main() -> None:
    count = seed_qdrant()
    seed_neo4j()
    print(f"Seed complete: {count} enablement programs indexed; Neo4j constraints created.")


if __name__ == "__main__":
    main()
