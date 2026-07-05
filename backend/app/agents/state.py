"""Shared, typed state passed between LangGraph nodes."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Inputs
    application_id: str
    applicant_name: str
    form_data: dict[str, Any]
    documents: list[dict[str, Any]]  # [{"doc_type": str, "path": str}]

    # Produced by the extraction agent
    extractions: list[dict[str, Any]]

    # Produced by the validation agent
    validation_flags: list[dict[str, Any]]  # [{field, severity, message}]
    validation_summary: str
    household: dict[str, Any]

    # Produced by the eligibility agent
    features: dict[str, Any]
    feature_notes: list[str]
    decision: dict[str, Any]

    # Produced by the recommendation agent
    recommendations: list[dict[str, Any]]

    # Errors
    error: str
