"""Recommendation agent: RAG over the Qdrant enablement knowledge base.

Retrieves the most relevant economic-enablement programs for the applicant's
profile and asks the LLM to produce 3 personalized recommendations.
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.common import set_status
from app.agents.prompts import RECOMMENDATION_SYSTEM
from app.agents.state import AgentState
from app.core.enums import ApplicationStatus, DocumentType
from app.core.logging import get_logger
from app.db import qdrant
from app.llm import client as llm

logger = get_logger(__name__)


def _profile_text(state: AgentState) -> str:
    f = state.get("features", {})
    by_type = {e.get("doc_type"): (e.get("structured") or {}) for e in state.get("extractions", [])}
    resume = by_type.get(DocumentType.RESUME, {})
    skills = resume.get("skills")
    skills_str = ", ".join(skills) if isinstance(skills, list) else (skills or "n/a")
    return (
        f"Employment status: {f.get('employment_status')}. "
        f"Education: {f.get('education_level')}. "
        f"Monthly income: AED {f.get('monthly_income', 0):,.0f}. "
        f"Family size: {int(f.get('family_size', 1))}, dependents: {int(f.get('num_dependents', 0))}. "
        f"Has disability: {f.get('has_disability')}. "
        f"Skills: {skills_str}. "
        f"Seeking upskilling, training, job matching, or career counseling."
    )


def recommendation_node(state: AgentState, config: dict | None = None) -> dict:
    app_id = state["application_id"]
    set_status(app_id, ApplicationStatus.RECOMMENDING, "Matching economic-enablement programs.")

    profile = _profile_text(state)

    # --- Retrieve (RAG) ---
    hits: list[dict] = []
    try:
        vector = llm.embed_query(profile)
        hits = qdrant.search(vector, limit=5)
    except Exception as exc:  # pragma: no cover
        logger.warning("KB retrieval failed: %s", exc)

    if not hits:
        return {"recommendations": []}

    # --- Generate personalized recommendations (LLM over retrieved programs) ---
    programs_text = "\n".join(
        f"- {h.get('title')} ({h.get('category')}): {h.get('description')}" for h in hits
    )
    try:
        content = llm.chat(
            [
                SystemMessage(content=RECOMMENDATION_SYSTEM),
                HumanMessage(
                    content=f"Applicant profile:\n{profile}\n\nAvailable programs:\n{programs_text}"
                ),
            ],
            temperature=0.3,
            json_mode=True,
            config=config,
        )
        data = json.loads(content)
        recs = data.get("recommendations", []) if isinstance(data, dict) else []
        if recs:
            return {"recommendations": recs[:3]}
    except Exception as exc:  # pragma: no cover
        logger.warning("Recommendation generation failed: %s", exc)

    # Fallback: return the top retrieved programs directly.
    fallback = [
        {"title": h.get("title"), "category": h.get("category"), "rationale": h.get("description")}
        for h in hits[:3]
    ]
    return {"recommendations": fallback}
