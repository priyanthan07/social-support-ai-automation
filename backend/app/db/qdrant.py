"""Qdrant vector-store client for the economic-enablement knowledge base."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, timeout=30)


def ensure_collection(vector_size: int) -> None:
    """Create the KB collection if it does not already exist."""
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s'", settings.qdrant_collection)


def upsert_points(points: list[PointStruct]) -> None:
    get_client().upsert(collection_name=settings.qdrant_collection, points=points)


def search(vector: list[float], limit: int = 4) -> list[dict[str, Any]]:
    """Return the top-k payloads (with scores) for a query vector."""
    client = get_client()
    results = client.query_points(
        collection_name=settings.qdrant_collection, query=vector, limit=limit, with_payload=True
    ).points
    return [{"score": r.score, **(r.payload or {})} for r in results]


def ping() -> bool:
    try:
        get_client().get_collections()
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("Qdrant ping failed: %s", exc)
        return False
