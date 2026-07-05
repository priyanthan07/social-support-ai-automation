"""Use the local LLM to structure raw document text into normalized JSON fields."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.llm import client as llm

logger = get_logger(__name__)

# Target fields per document type. The LLM is instructed to return exactly these.
FIELD_SCHEMAS: dict[str, dict[str, str]] = {
    "emirates_id": {
        "name": "full name",
        "id_number": "Emirates ID number",
        "date_of_birth": "YYYY-MM-DD",
        "nationality": "nationality",
        "address": "residential address",
        "expiry": "card expiry date",
    },
    "bank_statement": {
        "account_holder": "account holder name",
        "address": "address if present",
        "average_monthly_income": "average monthly credited/salary amount as a number",
        "total_credits": "sum of credits as a number",
        "total_debits": "sum of debits as a number",
    },
    "resume": {
        "name": "candidate name",
        "education": "highest education",
        "total_experience_years": "total years of work experience as a number",
        "employment_history": "list of {employer, role, period}",
        "skills": "list of skills",
    },
    "credit_report": {
        "name": "full name",
        "address": "registered address",
        "credit_score": "credit score as a number",
        "total_liabilities": "total outstanding liabilities as a number",
    },
}

_SYSTEM = (
    "You are a precise document data-extraction system for a government social "
    "support department. Extract ONLY the requested fields from the document text. "
    "Return a single valid JSON object with exactly the requested keys. Use null "
    "for anything not found. Do not invent values. Numbers must be plain numbers "
    "without currency symbols or commas."
)


def structure_fields(
    doc_type: str, raw_text: str, config: dict | None = None
) -> dict[str, Any]:
    """Return structured fields for the given document type using the LLM."""
    schema = FIELD_SCHEMAS.get(doc_type)
    if not schema or not raw_text.strip():
        return {}

    fields_desc = "\n".join(f'- "{k}": {v}' for k, v in schema.items())
    human = (
        f"Document type: {doc_type}\n"
        f"Extract these fields as JSON:\n{fields_desc}\n\n"
        f"Document text:\n\"\"\"\n{raw_text[:6000]}\n\"\"\""
    )
    try:
        content = llm.chat(
            [SystemMessage(content=_SYSTEM), HumanMessage(content=human)],
            temperature=0.0,
            json_mode=True,
            config=config,
        )
        data = json.loads(content)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON for %s extraction.", doc_type)
        return {}
    except Exception as exc:  # pragma: no cover
        logger.warning("LLM structuring failed for %s: %s", doc_type, exc)
        return {}
