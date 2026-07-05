"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.db import mongo, neo4j, qdrant
from app.db.session import ping as postgres_ping
from app.ml.model import get_model

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@router.get("/health/ready")
def readiness() -> dict:
    model = get_model()
    core = {
        "postgres": postgres_ping(),
        "mongodb": mongo.ping(),
        "qdrant": qdrant.ping(),
        "neo4j": neo4j.ping(),
        "ml_artifacts": model.available,
    }
    checks = {**core, "langfuse": settings.langfuse_ready}
    return {"status": "ready" if all(core.values()) else "degraded", "checks": checks}
