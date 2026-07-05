"""Eligibility agent: hard rules + scikit-learn score + LLM explanation.

The scikit-learn model owns the quantitative decision; policy gates can
override it; the LLM only produces a human-readable narrative. This directly
addresses the brief's "subjective decision-making / bias" pain point by making
the decision deterministic and auditable.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.common import set_status
from app.agents.prompts import ELIGIBILITY_NARRATIVE_SYSTEM
from app.agents.state import AgentState
from app.core.enums import ApplicationStatus, DecisionOutcome
from app.core.logging import get_logger
from app.llm import client as llm
from app.ml.features import assemble_features
from app.ml.model import get_model
from app.ml.rules import check_pre_gates

logger = get_logger(__name__)


def _factor_reasons(features: dict, model) -> list[str]:
    """Translate the top model features + applicant values into plain reasons."""
    reasons: list[str] = []
    importance = model.feature_importance(top_n=6)
    for feat in importance:
        val = features.get(feat)
        if feat == "income_per_capita":
            reasons.append(f"Income per household member is AED {val:,.0f}/month.")
        elif feat == "monthly_income":
            reasons.append(f"Household monthly income is AED {val:,.0f}.")
        elif feat == "net_worth":
            reasons.append(f"Net worth (assets minus liabilities) is AED {val:,.0f}.")
        elif feat == "employment_status":
            reasons.append(f"Employment status: {val}.")
        elif feat == "num_dependents":
            reasons.append(f"Number of dependents: {int(val)}.")
        elif feat == "family_size":
            reasons.append(f"Household size: {int(val)}.")
        if len(reasons) >= 3:
            break
    return reasons


def _narrative(outcome: str, reasons: list[str], config: dict | None) -> str:
    try:
        human = f"Decision: {outcome}\nKey factors:\n" + "\n".join(f"- {r}" for r in reasons)
        return llm.chat(
            [SystemMessage(content=ELIGIBILITY_NARRATIVE_SYSTEM), HumanMessage(content=human)],
            temperature=0.3,
            config=config,
        ).strip()
    except Exception as exc:  # pragma: no cover
        logger.warning("Eligibility narrative failed: %s", exc)
        return ""


def _present_doc_types(extractions: list[dict]) -> set[str]:
    """Doc types with successful extraction (failed/empty required docs excluded)."""
    present: set[str] = set()
    for ext in extractions:
        doc_type = ext.get("doc_type")
        if not doc_type or ext.get("error"):
            continue
        structured = ext.get("structured") or {}
        if not structured:
            continue
        present.add(doc_type)
    return present


def eligibility_node(state: AgentState, config: dict | None = None) -> dict:
    app_id = state["application_id"]
    set_status(app_id, ApplicationStatus.SCORING, "Assessing eligibility (rules + ML model).")

    form = state.get("form_data", {})
    extractions = state.get("extractions", [])
    validation_flags = state.get("validation_flags", [])

    features, notes = assemble_features(form, extractions)
    present_docs = _present_doc_types(extractions)

    reasons: list[str] = []
    outcome: str | None = None
    probability: float | None = None
    support_amount = 0.0
    confidence: float | None = None
    auto_decision = True

    model = get_model()

    # --- Pre-gates (policy overrides) ---
    gates = check_pre_gates(features, present_docs)
    if gates:
        forced = gates[0]
        outcome = forced.outcome
        reasons.extend(g.reason for g in gates)
        auto_decision = outcome != DecisionOutcome.NEEDS_REVIEW

    # --- ML score (if not force-decided) ---
    if outcome is None:
        try:
            pred = model.predict(features)
            probability = pred["probability"]
            confidence = pred["confidence"]
            meta = model.metadata
            threshold = meta.get("decision_threshold", 0.5)
            band = meta.get("review_band", [0.4, 0.6])
            if band[0] <= probability <= band[1]:
                outcome = DecisionOutcome.NEEDS_REVIEW
                auto_decision = False
                reasons.append("Model confidence is low near the decision boundary; flagged for human review.")
            elif probability >= threshold:
                outcome = DecisionOutcome.APPROVE
                support_amount = pred["support_amount"]
            else:
                outcome = DecisionOutcome.SOFT_DECLINE
        except Exception as exc:
            logger.warning("ML scoring failed: %s", exc)
            outcome = DecisionOutcome.NEEDS_REVIEW
            auto_decision = False
            reasons.append("Scoring model unavailable; manual review required.")

    reasons.extend(_factor_reasons(features, model))

    # High-severity discrepancies pull the decision out of full automation.
    if any(f.get("severity") == "high" for f in validation_flags):
        auto_decision = False
        reasons.append("High-severity data discrepancies require officer confirmation.")

    narrative = _narrative(outcome, reasons, config)

    decision = {
        "outcome": str(outcome),
        "eligibility_probability": probability,
        "support_amount": round(support_amount, 2),
        "confidence": confidence,
        "auto_decision": auto_decision,
        "reasons": reasons,
        "narrative": narrative,
    }
    return {"features": features, "feature_notes": notes, "decision": decision}
