"""Helpers shared by agent nodes (status transitions + audit logging)."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.logging import get_logger
from app.db.session import session_scope
from app.repositories import application_repository as repo

logger = get_logger(__name__)


def set_status(
    application_id: str,
    status: str,
    message: str,
    payload: dict[str, Any] | None = None,
    error: str | None = None,
    *,
    clear_error: bool = False,
) -> None:
    """Update the application status and append an audit-log entry."""
    try:
        app_uuid = uuid.UUID(application_id)
        with session_scope() as db:
            repo.update_status(
                db, app_uuid, status, error=error, clear_error=clear_error
            )
            repo.add_audit(db, app_uuid, stage=status, message=message, payload=payload)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to set status for %s: %s", application_id, exc)


def get_callbacks_from_config(config: dict | None) -> list:
    if not config:
        return []
    cb = config.get("callbacks")
    if cb is None:
        return []
    return cb if isinstance(cb, list) else [cb]
