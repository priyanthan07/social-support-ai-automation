"""Feature assembly tests."""

from app.ml.features import assemble_features


def test_assemble_prefers_bank_income():
    form = {
        "monthly_income": 5000,
        "family_size": 4,
        "num_dependents": 2,
        "employment_status": "unemployed",
        "housing_status": "rented",
        "education_level": "high_school",
        "marital_status": "married",
        "nationality_group": "citizen",
        "has_disability": "no",
    }
    extractions = [
        {
            "doc_type": "bank_statement",
            "structured": {"average_monthly_income": 1800},
        }
    ]
    features, notes = assemble_features(form, extractions)
    assert features["monthly_income"] == 1800
    assert any("bank-statement" in n for n in notes)
