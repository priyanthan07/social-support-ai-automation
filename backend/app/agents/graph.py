"""Master orchestrator: the LangGraph supervisor workflow + pipeline runner.

Flow:  extraction -> validation -> eligibility -> (conditional) -> recommendation

The conditional edge is the supervisor's routing decision: applications that
need human review (e.g. missing required documents) skip the recommendation
step and finish, while approvable / soft-declined applications proceed to
economic-enablement matching.
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.common import set_status
from app.agents.eligibility import eligibility_node
from app.agents.extraction import extraction_node
from app.agents.recommendation import recommendation_node
from app.agents.state import AgentState
from app.agents.validation import validation_node
from app.core.enums import ApplicationStatus, DecisionOutcome
from app.core.logging import get_logger
from app.db.session import session_scope
from app.ml.model import get_model
from app.observability import langfuse_client
from app.repositories import application_repository as repo

logger = get_logger(__name__)


def _route_after_eligibility(state: AgentState) -> str:
    decision = state.get("decision", {})
    if decision.get("outcome") == DecisionOutcome.NEEDS_REVIEW:
        return "finish"
    return "recommend"


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("extraction", extraction_node)
    builder.add_node("validation", validation_node)
    builder.add_node("eligibility", eligibility_node)
    builder.add_node("recommendation", recommendation_node)

    builder.add_edge(START, "extraction")
    builder.add_edge("extraction", "validation")
    builder.add_edge("validation", "eligibility")
    builder.add_conditional_edges(
        "eligibility",
        _route_after_eligibility,
        {"recommend": "recommendation", "finish": END},
    )
    builder.add_edge("recommendation", END)
    return builder.compile()


@lru_cache
def get_compiled_graph():
    return build_graph()


def run_pipeline(application_id: str) -> None:
    """Load the application, run the agent graph, and persist the decision.

    Intended to run in a background worker thread.
    """
    app_uuid = uuid.UUID(application_id)

    with session_scope() as db:
        app = repo.get_application(db, app_uuid)
        if app is None:
            logger.error("Application %s not found; aborting pipeline.", application_id)
            return
        if app.status == ApplicationStatus.DECIDED:
            logger.info("Application %s already decided; skipping pipeline.", application_id)
            return
        documents = [
            {"doc_type": d.doc_type, "path": d.storage_path}
            for d in repo.get_documents(db, app_uuid)
        ]
        initial_state: AgentState = {
            "application_id": application_id,
            "applicant_name": app.applicant_name,
            "form_data": app.form_data or {},
            "documents": documents,
        }

    graph = get_compiled_graph()
    config = {
        "callbacks": langfuse_client.get_callbacks(),
        "run_name": "social_support_application",
        "metadata": {"application_id": application_id},
    }

    try:
        final_state = graph.invoke(initial_state, config=config)
        _persist_result(app_uuid, final_state)
    except Exception as exc:
        logger.exception("Pipeline failed for %s: %s", application_id, exc)
        set_status(
            application_id,
            ApplicationStatus.FAILED,
            f"Processing failed: {exc}",
            error=str(exc),
        )
    finally:
        langfuse_client.flush()


def _persist_result(app_uuid: uuid.UUID, state: AgentState) -> None:
    decision = state.get("decision", {})
    model_meta = {
        "narrative": decision.get("narrative", ""),
        "validation_summary": state.get("validation_summary", ""),
        "feature_notes": state.get("feature_notes", []),
        "household": state.get("household", {}),
        "model_version": get_model().metadata.get("trained_at", "unknown"),
    }
    with session_scope() as db:
        repo.save_decision(
            db,
            app_uuid,
            outcome=decision.get("outcome", DecisionOutcome.NEEDS_REVIEW),
            eligibility_probability=decision.get("eligibility_probability"),
            support_amount=decision.get("support_amount", 0.0) or 0.0,
            confidence=decision.get("confidence"),
            auto_decision=decision.get("auto_decision", True),
            reasons=decision.get("reasons", []),
            validation_flags=state.get("validation_flags", []),
            recommendations=state.get("recommendations", []),
            features=state.get("features", {}),
            model_metadata=model_meta,
        )
        repo.update_status(db, app_uuid, ApplicationStatus.DECIDED, clear_error=True)
        repo.add_audit(
            db,
            app_uuid,
            stage=ApplicationStatus.DECIDED,
            message=f"Decision: {decision.get('outcome')}",
            payload={"auto_decision": decision.get("auto_decision")},
        )
