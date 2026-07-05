"""Grounded chat agent: answers applicant questions about their case + programs."""

from __future__ import annotations

import uuid

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.prompts import CHAT_SYSTEM
from app.core.logging import get_logger
from app.db import mongo, qdrant
from app.db.session import session_scope
from app.llm import client as llm
from app.observability import langfuse_client
from app.repositories import application_repository as repo

logger = get_logger(__name__)


def _application_context(application_id: str) -> str:
    try:
        app = repo_get(application_id)
    except Exception:
        return "No application context available."
    if app is None:
        return "No application found for this reference."

    lines = [
        f"Applicant: {app.applicant_name}",
        f"Application status: {app.status}",
    ]
    if app.decision is not None:
        d = app.decision
        lines.append(f"Decision: {d.outcome} (auto-decision: {d.auto_decision})")
        if d.support_amount:
            lines.append(f"Recommended monthly support: AED {d.support_amount:,.0f}")
        if d.reasons:
            lines.append("Key factors: " + "; ".join(d.reasons[:4]))
        if d.recommendations:
            titles = [r.get("title", "") for r in d.recommendations]
            lines.append("Recommended programs: " + ", ".join(t for t in titles if t))
    return "\n".join(lines)


def repo_get(application_id: str):
    with session_scope() as db:
        return repo.get_application(db, uuid.UUID(application_id))


def _kb_context(question: str) -> str:
    try:
        hits = qdrant.search(llm.embed_query(question), limit=3)
    except Exception:
        return ""
    if not hits:
        return ""
    return "Relevant programs:\n" + "\n".join(
        f"- {h.get('title')}: {h.get('description')}" for h in hits
    )


def answer_question(application_id: str, question: str) -> str:
    """Answer a question grounded in the application context + knowledge base."""
    context = _application_context(application_id)
    kb = _kb_context(question)

    messages = [SystemMessage(content=CHAT_SYSTEM)]
    # Recent history for continuity.
    try:
        for turn in mongo.get_chat_history(application_id, limit=10):
            role = turn.get("role")
            content = turn.get("content", "")
            messages.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
    except Exception:  # pragma: no cover
        pass

    prompt = f"Application context:\n{context}\n\n{kb}\n\nQuestion: {question}"
    messages.append(HumanMessage(content=prompt))

    config = {"callbacks": langfuse_client.get_callbacks(), "run_name": "chat"}
    try:
        answer = llm.chat(messages, temperature=0.3, config=config)
    except Exception as exc:  # pragma: no cover
        logger.warning("Chat failed: %s", exc)
        answer = "I'm sorry, I couldn't process that right now. Please try again shortly."
    finally:
        langfuse_client.flush()

    try:
        mongo.save_chat_turn(application_id, "user", question)
        mongo.save_chat_turn(application_id, "assistant", answer)
    except Exception:  # pragma: no cover
        pass
    return answer
