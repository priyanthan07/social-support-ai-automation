"""MongoDB client: stores raw document metadata + flexible extraction JSON."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

EXTRACTIONS_COLLECTION = "document_extractions"
CHAT_COLLECTION = "chat_history"


@lru_cache
def get_client() -> MongoClient:
    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)


def get_db() -> Database:
    return get_client()[settings.mongo_db]


def save_extraction(application_id: str, doc_type: str, payload: dict[str, Any]) -> str:
    """Persist a document's raw text + structured extraction. Returns the Mongo _id."""
    coll = get_db()[EXTRACTIONS_COLLECTION]
    doc = {"application_id": application_id, "doc_type": doc_type, **payload}
    result = coll.insert_one(doc)
    return str(result.inserted_id)


def get_extractions(application_id: str) -> list[dict[str, Any]]:
    coll = get_db()[EXTRACTIONS_COLLECTION]
    docs = list(coll.find({"application_id": application_id}))
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


def save_chat_turn(application_id: str, role: str, content: str) -> None:
    get_db()[CHAT_COLLECTION].insert_one(
        {"application_id": application_id, "role": role, "content": content}
    )


def get_chat_history(application_id: str, limit: int = 50) -> list[dict[str, Any]]:
    coll = get_db()[CHAT_COLLECTION]
    docs = list(coll.find({"application_id": application_id}).limit(limit))
    return [{"role": d.get("role"), "content": d.get("content")} for d in docs]


def ping() -> bool:
    try:
        get_client().admin.command("ping")
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("MongoDB ping failed: %s", exc)
        return False
