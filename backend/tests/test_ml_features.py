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


def test_resume_merges_employment_and_education():
    form = {
        "monthly_income": 1800,
        "family_size": 4,
        "num_dependents": 2,
        "employment_status": "unemployed",
        "housing_status": "rented",
        "education_level": "high_school",
        "marital_status": "married",
        "nationality_group": "citizen",
        "has_disability": "no",
        "employment_years": 0.0,
        "months_employed_last_2yrs": 0,
    }
    extractions = [
        {
            "doc_type": "resume",
            "structured": {
                "total_experience_years": 8,
                "education": "Bachelor of Science",
                "employment_history": [{"company": "Acme", "years": 3}],
            },
        }
    ]
    features, notes = assemble_features(form, extractions)
    assert features["employment_years"] == 8
    assert features["education_level"] == "bachelor"
    assert features["months_employed_last_2yrs"] == 24
    assert any("resume" in n.lower() for n in notes)


def test_emirates_id_dob_derives_age():
    form = {
        "monthly_income": 1800,
        "family_size": 4,
        "num_dependents": 2,
        "employment_status": "unemployed",
        "housing_status": "rented",
        "education_level": "high_school",
        "marital_status": "married",
        "nationality_group": "citizen",
        "has_disability": "no",
        "age": 35,
    }
    extractions = [
        {
            "doc_type": "emirates_id",
            "structured": {"date_of_birth": "1988-03-15"},
        }
    ]
    features, notes = assemble_features(form, extractions)
    assert features["age"] >= 30
    assert any("date of birth" in n.lower() for n in notes)


def test_emirates_id_dob_does_not_override_explicit_form_age():
    form = {
        "monthly_income": 1800,
        "family_size": 4,
        "num_dependents": 2,
        "employment_status": "unemployed",
        "housing_status": "rented",
        "education_level": "high_school",
        "marital_status": "married",
        "nationality_group": "citizen",
        "has_disability": "no",
        "age": 42,
    }
    extractions = [
        {
            "doc_type": "emirates_id",
            "structured": {"date_of_birth": "1988-03-15"},
        }
    ]
    features, notes = assemble_features(form, extractions)
    assert features["age"] == 42
    assert not any("date of birth" in n.lower() for n in notes)


def test_credit_score_zero_when_no_credit_report():
    form = {
        "monthly_income": 1800,
        "family_size": 4,
        "num_dependents": 2,
        "employment_status": "unemployed",
        "housing_status": "rented",
        "education_level": "high_school",
        "marital_status": "married",
        "nationality_group": "citizen",
        "has_disability": "no",
    }
    features, _notes = assemble_features(form, [])
    assert features["credit_score"] == 0.0
