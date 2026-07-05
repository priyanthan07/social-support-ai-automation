"""Validation agent: cross-document consistency + household graph + Reflexion.

Deterministically detects discrepancies (address, income, name) across the
form and extracted documents, models the household in Neo4j (surfacing shared
addresses = possible duplicates), then runs an LLM Reflexion pass that reviews
the flags and writes a concise officer-facing summary.
"""

from __future__ import annotations

import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.common import set_status
from app.agents.prompts import VALIDATION_REFLEXION_SYSTEM
from app.agents.state import AgentState
from app.core.enums import ApplicationStatus, DocumentType
from app.core.logging import get_logger
from app.db import neo4j
from app.llm import client as llm

logger = get_logger(__name__)


def _normalize(text: str | None) -> set[str]:
    if not text:
        return set()
    tokens = re.split(r"[\s,./-]+", str(text).lower())
    return {t for t in tokens if len(t) > 2}


def _overlap(a: str | None, b: str | None) -> float:
    ta, tb = _normalize(a), _normalize(b)
    if not ta or not tb:
        return 1.0  # cannot compare -> not a mismatch
    return len(ta & tb) / len(ta | tb)


def _by_type(extractions: list[dict]) -> dict[str, dict]:
    return {e.get("doc_type"): (e.get("structured") or {}) for e in extractions}


def validation_node(state: AgentState, config: dict | None = None) -> dict:
    app_id = state["application_id"]
    set_status(app_id, ApplicationStatus.VALIDATING, "Cross-checking document consistency.")

    form = state.get("form_data", {})
    by_type = _by_type(state.get("extractions", []))
    eid = by_type.get(DocumentType.EMIRATES_ID, {})
    credit = by_type.get(DocumentType.CREDIT_REPORT, {})
    bank = by_type.get(DocumentType.BANK_STATEMENT, {})
    resume = by_type.get(DocumentType.RESUME, {})

    flags: list[dict] = []

    # --- Address consistency (Emirates ID vs credit report vs form) ---
    addr_id = eid.get("address")
    addr_credit = credit.get("address")
    addr_form = form.get("address")
    if addr_id and addr_credit and _overlap(addr_id, addr_credit) < 0.6:
        flags.append(
            {
                "field": "address",
                "severity": "medium",
                "message": f"Address differs between Emirates ID ('{addr_id}') and credit report ('{addr_credit}').",
            }
        )
    if addr_id and addr_form and _overlap(addr_id, addr_form) < 0.5:
        flags.append(
            {
                "field": "address",
                "severity": "low",
                "message": "Address on the form differs from the Emirates ID.",
            }
        )

    # --- Income consistency (form vs bank statement) ---
    try:
        form_income = float(form.get("monthly_income") or 0)
        bank_income = float(bank.get("average_monthly_income") or 0)
        if bank_income > 0 and form_income > 0:
            variance = abs(form_income - bank_income) / max(form_income, bank_income)
            if variance > 0.2:
                flags.append(
                    {
                        "field": "income",
                        "severity": "high",
                        "message": (
                            f"Declared income (AED {form_income:,.0f}) differs from bank "
                            f"statement (AED {bank_income:,.0f}) by {variance:.0%}."
                        ),
                    }
                )
    except (ValueError, TypeError):
        pass

    # --- Name consistency (Emirates ID vs resume) ---
    if eid.get("name") and resume.get("name") and _overlap(eid.get("name"), resume.get("name")) < 0.4:
        flags.append(
            {
                "field": "name",
                "severity": "low",
                "message": "Name on the resume differs from the Emirates ID.",
            }
        )

    # --- Household graph (Neo4j) + duplicate-address detection ---
    household: dict = {}
    address = addr_id or addr_form
    try:
        family_members = form.get("family_members") or []
        neo4j.upsert_household(app_id, state.get("applicant_name", ""), address, family_members)
        shared = neo4j.find_shared_address_applicants(app_id, address)
        if shared:
            flags.append(
                {
                    "field": "duplicate",
                    "severity": "high",
                    "message": f"{len(shared)} other application(s) share this address (possible duplicate/fraud).",
                }
            )
        household = neo4j.household_snapshot(app_id)
    except Exception as exc:  # pragma: no cover
        logger.warning("Neo4j household step failed: %s", exc)

    # --- Reflexion: LLM reviews the flags and writes a summary ---
    summary = _reflexion_summary(flags, config)

    return {"validation_flags": flags, "validation_summary": summary, "household": household}


def _reflexion_summary(flags: list[dict], config: dict | None) -> str:
    if not flags:
        return "All documents are consistent. No discrepancies detected."
    flag_text = "\n".join(f"- [{f['severity']}] {f['field']}: {f['message']}" for f in flags)
    try:
        return llm.chat(
            [
                SystemMessage(content=VALIDATION_REFLEXION_SYSTEM),
                HumanMessage(content=f"Detected flags:\n{flag_text}"),
            ],
            temperature=0.2,
            config=config,
        ).strip()
    except Exception as exc:  # pragma: no cover
        logger.warning("Reflexion summary failed: %s", exc)
        return f"{len(flags)} potential discrepancy(ies) detected; manual review advised."
