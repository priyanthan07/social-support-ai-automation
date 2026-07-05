"""Validation cross-check tests."""

from unittest.mock import patch

from app.agents.text_match import text_overlap
from app.agents.validation import validation_node


def test_address_overlap_detects_mismatch():
    assert text_overlap("Villa 12, Al Wathba, Abu Dhabi", "Marina Heights, Dubai") < 0.3


def test_address_overlap_detects_match():
    assert text_overlap("Villa 12, Al Wathba, Abu Dhabi", "Villa 12 Al Wathba Abu Dhabi") > 0.5


def test_address_overlap_empty_tokens_returns_zero():
    assert text_overlap("   ", "Villa 12, Al Wathba, Abu Dhabi") == 0.0
    assert text_overlap("", "Marina Heights, Dubai") == 0.0


@patch("app.agents.validation.run_react_loop", return_value="ReAct summary.")
@patch("app.agents.validation.llm.chat", return_value="Refined summary.")
@patch("app.agents.validation.neo4j.upsert_household")
@patch("app.agents.validation.neo4j.find_shared_address_applicants", return_value=[])
@patch("app.agents.validation.neo4j.household_snapshot", return_value={})
def test_validation_runs_react_when_flags_exist(
    mock_snapshot, mock_shared, mock_upsert, mock_llm_chat, mock_react
):
    state = {
        "application_id": "app-1",
        "applicant_name": "Test User",
        "form_data": {"monthly_income": 5000, "address": "A", "family_members": []},
        "extractions": [
            {
                "doc_type": "emirates_id",
                "structured": {"address": "A", "name": "Test User"},
            },
            {
                "doc_type": "credit_report",
                "structured": {"address": "Completely Different Place Dubai Marina"},
            },
            {
                "doc_type": "bank_statement",
                "structured": {"average_monthly_income": 5000},
            },
        ],
    }
    result = validation_node(state)
    assert result["validation_flags"]
    mock_react.assert_called_once()
    assert result["validation_summary"] == "Refined summary."


@patch("app.agents.validation.neo4j.upsert_household")
@patch("app.agents.validation.neo4j.find_shared_address_applicants", return_value=[])
@patch("app.agents.validation.neo4j.household_snapshot", return_value={})
def test_validation_skips_react_when_no_flags(mock_snapshot, mock_shared, mock_upsert):
    state = {
        "application_id": "app-1",
        "applicant_name": "Test User",
        "form_data": {"address": "Same place", "family_members": [], "monthly_income": 5000},
        "extractions": [
            {
                "doc_type": "emirates_id",
                "structured": {"address": "Same place", "name": "Test User"},
            },
            {
                "doc_type": "credit_report",
                "structured": {"address": "Same place"},
            },
            {
                "doc_type": "bank_statement",
                "structured": {"average_monthly_income": 5000},
            },
        ],
    }
    result = validation_node(state)
    assert result["validation_flags"] == []
    assert result["validation_summary"] == "All documents are consistent. No discrepancies detected."
