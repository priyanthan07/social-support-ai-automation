"""Validation agent: cross-document consistency + household graph + ReAct + Reflexion."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.common import set_status
from app.agents.prompts import VALIDATION_REACT_SYSTEM, VALIDATION_REFLEXION_SYSTEM
from app.agents.react_loop import run_react_loop
from app.agents.state import AgentState
from app.agents.text_match import text_overlap
from app.agents.tools.validation_tools import ValidationToolContext, build_validation_tools
from app.core.enums import ApplicationStatus, DocumentType
from app.core.logging import get_logger
from app.db import neo4j
from app.llm import client as llm

logger = get_logger(__name__)


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

    addr_id = eid.get("address")
    addr_credit = credit.get("address")
    addr_form = form.get("address")
    if addr_id and addr_credit and text_overlap(addr_id, addr_credit) < 0.6:
        flags.append(
            {
                "field": "address",
                "severity": "medium",
                "message": f"Address differs between Emirates ID ('{addr_id}') and credit report ('{addr_credit}').",
            }
        )
    if addr_id and addr_form and text_overlap(addr_id, addr_form) < 0.5:
        flags.append(
            {
                "field": "address",
                "severity": "low",
                "message": "Address on the form differs from the Emirates ID.",
            }
        )

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

    if eid.get("name") and resume.get("name") and text_overlap(eid.get("name"), resume.get("name")) < 0.4:
        flags.append(
            {
                "field": "name",
                "severity": "low",
                "message": "Name on the resume differs from the Emirates ID.",
            }
        )

    household: dict = {}
    address = addr_id or addr_form
    shared: list[str] = []
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

    summary = _validation_summary(
        state, flags, household, address, by_type, form, config, shared
    )

    return {"validation_flags": flags, "validation_summary": summary, "household": household}


def _validation_summary(
    state: AgentState,
    flags: list[dict],
    household: dict,
    address: str | None,
    by_type: dict[str, dict],
    form: dict,
    config: dict | None,
    shared_address_applicants: list[str],
) -> str:
    if not flags:
        return "All documents are consistent. No discrepancies detected."

    flag_text = "\n".join(f"- [{f['severity']}] {f['field']}: {f['message']}" for f in flags)
    ctx = ValidationToolContext(
        flags=flags,
        form_data=form,
        extractions_by_type=by_type,
        application_id=state["application_id"],
        household=household,
        address=address,
        shared_address_applicants=shared_address_applicants,
    )
    tools = build_validation_tools(ctx)

    try:
        summary = run_react_loop(
            system_prompt=VALIDATION_REACT_SYSTEM,
            user_prompt=(
                f"Applicant: {state.get('applicant_name', '')}\n"
                f"Detected flags:\n{flag_text}\n\n"
                "Use tools to verify evidence, then write a concise 2-3 sentence officer summary."
            ),
            tools=tools,
            config=config,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Validation ReAct loop failed: %s", exc)
        summary = f"{len(flags)} potential discrepancy(ies) detected; manual review advised."

    return _reflexion_critique(summary, flags, config)


def _reflexion_critique(summary: str, flags: list[dict], config: dict | None) -> str:
    """Optional self-critique pass on the ReAct-produced summary."""
    flag_text = "\n".join(f"- [{f['severity']}] {f['field']}: {f['message']}" for f in flags)
    try:
        refined = llm.chat(
            [
                SystemMessage(content=VALIDATION_REFLEXION_SYSTEM),
                HumanMessage(
                    content=f"Flags:\n{flag_text}\n\nDraft summary:\n{summary}\n\n"
                    "Review the draft. Return an improved 2-3 sentence summary only."
                ),
            ],
            temperature=0.2,
            config=config,
        ).strip()
        return refined or summary
    except Exception as exc:  # pragma: no cover
        logger.warning("Reflexion critique failed: %s", exc)
        return summary
