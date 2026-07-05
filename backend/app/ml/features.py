"""Assemble the canonical model feature vector from form + extracted documents.

Document evidence is preferred over self-reported form values where available
(e.g. bank-statement income, credit-report score, assets/liabilities totals).
Returns the feature dict plus provenance notes used for transparency.
"""

from __future__ import annotations

from typing import Any

NUMERIC_DEFAULTS: dict[str, float] = {
    "monthly_income": 0.0,
    "income_per_capita": 0.0,
    "family_size": 1,
    "num_dependents": 0,
    "age": 35,
    "employment_years": 0.0,
    "months_employed_last_2yrs": 0,
    "total_assets": 0.0,
    "total_liabilities": 0.0,
    "net_worth": 0.0,
    "credit_score": 600,
}

CATEGORICAL_DEFAULTS: dict[str, str] = {
    "employment_status": "unemployed",
    "housing_status": "rented",
    "education_level": "high_school",
    "marital_status": "single",
    "nationality_group": "citizen",
    "has_disability": "no",
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "").replace("AED", "").strip())
    except (ValueError, TypeError):
        return default


def _extraction_by_type(extractions: list[dict]) -> dict[str, dict]:
    """Index extraction payloads by doc_type -> structured dict."""
    out: dict[str, dict] = {}
    for ext in extractions:
        doc_type = ext.get("doc_type")
        structured = ext.get("structured") or {}
        if doc_type:
            out[doc_type] = structured
    return out


def assemble_features(
    form_data: dict[str, Any], extractions: list[dict]
) -> tuple[dict[str, Any], list[str]]:
    """Return (features, provenance_notes)."""
    by_type = _extraction_by_type(extractions)
    notes: list[str] = []

    features: dict[str, Any] = {}
    # Start from form-provided values with defaults.
    for key, default in NUMERIC_DEFAULTS.items():
        features[key] = _to_float(form_data.get(key), default)
    for key, default in CATEGORICAL_DEFAULTS.items():
        features[key] = str(form_data.get(key) or default)

    # Prefer bank-statement income over self-reported.
    bank = by_type.get("bank_statement", {})
    bank_income = _to_float(bank.get("average_monthly_income"), 0.0)
    if bank_income > 0:
        if abs(bank_income - features["monthly_income"]) > 500:
            notes.append(
                f"Income adjusted to bank-statement value AED {bank_income:,.0f} "
                f"(form stated AED {features['monthly_income']:,.0f})."
            )
        features["monthly_income"] = bank_income

    # Credit score from credit report.
    credit = by_type.get("credit_report", {})
    credit_score = _to_float(credit.get("credit_score"), 0.0)
    if credit_score > 0:
        features["credit_score"] = credit_score

    # Assets / liabilities from the Excel extraction.
    assets = by_type.get("assets_liabilities", {})
    if assets:
        features["total_assets"] = _to_float(assets.get("total_assets"), features["total_assets"])
        features["total_liabilities"] = _to_float(
            assets.get("total_liabilities"), features["total_liabilities"]
        )
        features["net_worth"] = _to_float(
            assets.get("net_worth"),
            features["total_assets"] - features["total_liabilities"],
        )
        notes.append("Assets/liabilities taken from uploaded financial file.")
    else:
        features["net_worth"] = features["total_assets"] - features["total_liabilities"]

    # Derived: income per capita.
    family_size = max(1.0, features["family_size"])
    features["income_per_capita"] = round(features["monthly_income"] / family_size, 2)

    return features, notes
