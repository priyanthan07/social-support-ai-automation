"""Extraction agent: parse each uploaded document into normalized JSON."""

from __future__ import annotations

from app.agents.common import set_status
from app.agents.state import AgentState
from app.core.enums import ApplicationStatus
from app.core.logging import get_logger
from app.db import mongo
from app.extractors import extract_document

logger = get_logger(__name__)


def extraction_node(state: AgentState, config: dict | None = None) -> dict:
    app_id = state["application_id"]
    documents = state.get("documents", [])
    set_status(
        app_id,
        ApplicationStatus.EXTRACTING,
        f"Extracting {len(documents)} document(s).",
    )

    extractions: list[dict] = []
    for doc in documents:
        doc_type = doc["doc_type"]
        try:
            result = extract_document(doc_type, doc["path"], config=config)
            payload = result.to_payload()
        except Exception as exc:  # pragma: no cover
            logger.warning("Extraction failed for %s: %s", doc_type, exc)
            payload = {"doc_type": doc_type, "structured": {}, "error": str(exc)}

        try:
            mongo.save_extraction(app_id, doc_type, payload)
        except Exception as exc:  # pragma: no cover
            logger.debug("Mongo save_extraction failed: %s", exc)

        extractions.append(payload)

    return {"extractions": extractions}
