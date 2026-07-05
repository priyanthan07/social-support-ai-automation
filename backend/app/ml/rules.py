"""Hard business/policy gates applied around the ML score.

These are non-negotiable policy constraints that can override the model
(safety + fairness). They run BEFORE and AFTER the ML score:

* Pre-gates can force NEEDS_REVIEW (e.g. missing critical data) or
  SOFT_DECLINE (e.g. clear wealth above policy limits).
* The ML probability decides the remaining (majority of) cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Policy thresholds (documented assumptions).
WEALTH_CEILING = 1_500_000.0        # net worth above which support is declined
INCOME_PC_CEILING = 8000.0          # monthly income per capita above which declined
MIN_REQUIRED_DOCS = {"emirates_id"}  # documents required to auto-decide


@dataclass
class GateResult:
    triggered: bool
    outcome: str | None = None          # forced outcome if triggered
    reason: str = ""


def check_pre_gates(features: dict[str, Any], present_doc_types: set[str]) -> list[GateResult]:
    """Return any triggered hard gates evaluated before scoring."""
    from app.core.enums import DecisionOutcome

    gates: list[GateResult] = []

    missing = MIN_REQUIRED_DOCS - present_doc_types
    if missing:
        gates.append(
            GateResult(
                triggered=True,
                outcome=DecisionOutcome.NEEDS_REVIEW,
                reason=f"Missing required document(s): {', '.join(sorted(missing))}.",
            )
        )

    if features.get("net_worth", 0) > WEALTH_CEILING:
        gates.append(
            GateResult(
                triggered=True,
                outcome=DecisionOutcome.SOFT_DECLINE,
                reason=(
                    f"Net worth AED {features['net_worth']:,.0f} exceeds the policy "
                    f"ceiling of AED {WEALTH_CEILING:,.0f}."
                ),
            )
        )

    if features.get("income_per_capita", 0) > INCOME_PC_CEILING:
        gates.append(
            GateResult(
                triggered=True,
                outcome=DecisionOutcome.SOFT_DECLINE,
                reason=(
                    f"Income per capita AED {features['income_per_capita']:,.0f} exceeds "
                    f"the policy ceiling of AED {INCOME_PC_CEILING:,.0f}."
                ),
            )
        )

    return [g for g in gates if g.triggered]
