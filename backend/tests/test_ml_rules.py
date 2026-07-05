"""Business rule gate tests."""

from app.core.enums import DecisionOutcome
from app.ml.rules import check_pre_gates


def test_wealth_ceiling_declines():
    features = {
        "net_worth": 2_000_000,
        "income_per_capita": 3000,
    }
    gates = check_pre_gates(features, {"emirates_id"})
    assert any(g.outcome == DecisionOutcome.SOFT_DECLINE for g in gates)


def test_missing_emirates_id_needs_review():
    features = {"net_worth": 10000, "income_per_capita": 3000}
    gates = check_pre_gates(features, set())
    assert any(g.outcome == DecisionOutcome.NEEDS_REVIEW for g in gates)
