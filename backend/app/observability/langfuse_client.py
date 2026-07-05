"""Langfuse observability integration (v4).

Provides a LangChain ``CallbackHandler`` that is attached to every LLM / agent
invocation so each application-processing run appears as one nested trace in
Langfuse. Safely degrades to a no-op when credentials are not configured.
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def _init() -> bool:
    """Initialize the global Langfuse client once. Returns True if active."""
    if not settings.langfuse_ready:
        logger.info("Langfuse disabled or not configured -- tracing is a no-op.")
        return False
    # Ensure the SDK (and the LangChain CallbackHandler) can read credentials.
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
    try:
        from langfuse import Langfuse

        Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info("Langfuse tracing enabled (host=%s).", settings.langfuse_host)
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to initialize Langfuse: %s", exc)
        return False


@lru_cache
def get_handler():
    """Return a cached Langfuse CallbackHandler, or ``None`` if disabled."""
    if not _init():
        return None
    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to create Langfuse CallbackHandler: %s", exc)
        return None


def get_callbacks() -> list:
    """Return the callbacks list to pass into LangChain/LangGraph ``config``."""
    handler = get_handler()
    return [handler] if handler is not None else []


def flush() -> None:
    """Flush pending traces (call at end of a processing run)."""
    if not settings.langfuse_ready:
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse flush failed: %s", exc)
