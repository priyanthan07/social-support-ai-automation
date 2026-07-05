"""LLM + embeddings client wrapper around a locally-hosted Ollama server.

Design notes:
* This is intentionally a thin, OpenAI-compatible-style wrapper so the backend
  can be pointed at vLLM / TGI in production by changing configuration only.
* A process-wide ``threading.BoundedSemaphore`` serializes LLM calls so a
  CPU-only Ollama instance is not overwhelmed when several applications are
  processed concurrently (each pipeline runs in its own worker thread).
"""

from __future__ import annotations

import threading
from functools import lru_cache

from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Serialize concurrent LLM calls to protect the local model.
_llm_semaphore = threading.BoundedSemaphore(max(1, settings.llm_max_concurrency))


@lru_cache
def get_chat_model(temperature: float = 0.1, json_mode: bool = False) -> ChatOllama:
    """Return a cached ChatOllama instance."""
    return ChatOllama(
        model=settings.ollama_llm_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
        format="json" if json_mode else None,
        num_ctx=8192,
        client_kwargs={"timeout": settings.ollama_request_timeout},
    )


@lru_cache
def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )


def chat(
    messages: list[BaseMessage],
    *,
    temperature: float = 0.1,
    json_mode: bool = False,
    config: dict | None = None,
    callbacks: list | None = None,
) -> str:
    """Invoke the chat model (serialized) and return the text content.

    ``config`` (a LangGraph/LangChain RunnableConfig) is propagated so calls
    nest correctly under the parent trace. ``callbacks`` is a convenience
    alternative when no full config is available.
    """
    model = get_chat_model(temperature=temperature, json_mode=json_mode)
    if config is None and callbacks:
        config = {"callbacks": callbacks}
    with _llm_semaphore:
        response = model.invoke(messages, config=config)
    return response.content if isinstance(response.content, str) else str(response.content)


def embed_documents(texts: list[str]) -> list[list[float]]:
    with _llm_semaphore:
        return get_embeddings().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    with _llm_semaphore:
        return get_embeddings().embed_query(text)
