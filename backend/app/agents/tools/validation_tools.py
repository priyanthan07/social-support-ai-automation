"""Read-only tools for the validation agent ReAct loop."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import StructuredTool

from app.agents.text_match import text_overlap


@dataclass
class ValidationToolContext:
    flags: list[dict[str, Any]]
    form_data: dict[str, Any]
    extractions_by_type: dict[str, dict]
    application_id: str
    household: dict[str, Any]
    address: str | None
    shared_address_applicants: list[str]


def build_validation_tools(ctx: ValidationToolContext) -> list[StructuredTool]:
    """Return LangChain tools bound to a single application validation context."""

    def list_detected_flags() -> str:
        """List automatically detected validation flags for this application."""
        return json.dumps(ctx.flags, ensure_ascii=False)

    def get_extraction(doc_type: str) -> str:
        """Return structured fields extracted from a document type (e.g. emirates_id, bank_statement)."""
        data = ctx.extractions_by_type.get(doc_type, {})
        return json.dumps(data, ensure_ascii=False)

    def get_form_field(field_name: str) -> str:
        """Return a value from the applicant's submitted form data."""
        value = ctx.form_data.get(field_name)
        return json.dumps(value, ensure_ascii=False)

    def compare_text_overlap(text_a: str, text_b: str) -> str:
        """Compare two text strings (e.g. addresses or names) and return overlap score 0-1."""
        score = text_overlap(text_a, text_b)
        return json.dumps({"overlap": round(score, 3), "text_a": text_a, "text_b": text_b})

    def get_household_snapshot() -> str:
        """Return the Neo4j household snapshot for this application."""
        return json.dumps(ctx.household or {}, ensure_ascii=False)

    def find_shared_address_applicants() -> str:
        """Return other application IDs registered at the same address, if any were detected."""
        return json.dumps(
            {
                "application_ids": ctx.shared_address_applicants,
                "address": ctx.address,
            },
            ensure_ascii=False,
        )

    return [
        StructuredTool.from_function(list_detected_flags),
        StructuredTool.from_function(get_extraction),
        StructuredTool.from_function(get_form_field),
        StructuredTool.from_function(compare_text_overlap),
        StructuredTool.from_function(get_household_snapshot),
        StructuredTool.from_function(find_shared_address_applicants),
    ]
