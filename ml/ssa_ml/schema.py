"""Canonical applicant feature schema.

This is the single source of truth for the model's input features. The trained
scikit-learn pipeline encodes these columns internally, and the backend builds
its inference row using the exact same names (persisted to
``model_metadata.json``).
"""

from __future__ import annotations

# Monetary amounts are monthly AED unless the name says otherwise.
NUMERIC_FEATURES: list[str] = [
    "monthly_income",
    "income_per_capita",
    "family_size",
    "num_dependents",
    "age",
    "employment_years",
    "months_employed_last_2yrs",
    "total_assets",
    "total_liabilities",
    "net_worth",
    "credit_score",
]

CATEGORICAL_FEATURES: list[str] = [
    "employment_status",
    "housing_status",
    "education_level",
    "marital_status",
    "nationality_group",
    "has_disability",
]

ALL_FEATURES: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Allowed categorical values (used by data generation and UI dropdowns).
CATEGORY_VALUES: dict[str, list[str]] = {
    "employment_status": ["employed", "self_employed", "unemployed", "retired", "student"],
    "housing_status": ["owned", "rented", "family", "government_housing"],
    "education_level": ["none", "high_school", "diploma", "bachelor", "postgraduate"],
    "marital_status": ["single", "married", "divorced", "widowed"],
    "nationality_group": ["citizen", "resident"],
    "has_disability": ["yes", "no"],
}

# Assumptions used throughout (documented in the solution summary).
POVERTY_LINE_PER_CAPITA = 4000.0  # monthly AED per household member
MAX_SUPPORT_AMOUNT = 15000.0      # monthly AED cap for financial support
MIN_SUPPORT_AMOUNT = 1000.0
TARGET_ELIGIBLE = "eligible"
TARGET_SUPPORT = "support_amount"
