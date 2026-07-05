"""Assemble the canonical model feature vector from form + extracted documents.

Document evidence is preferred over self-reported form values where available
(e.g. bank-statement income, credit-report score, assets/liabilities totals).
Returns the feature dict plus provenance notes used for transparency.
"""

from __future__ import annotations

from datetime import date, datetime
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

EDUCATION_LEVEL_VALUES = {
    "none",
    "high_school",
    "diploma",
    "bachelor",
    "postgraduate",
}

EDUCATION_ALIASES: list[tuple[str, str]] = [
    ("postgraduate", "postgraduate"),
    ("master", "postgraduate"),
    ("phd", "postgraduate"),
    ("doctorate", "postgraduate"),
    ("bachelor", "bachelor"),
    ("diploma", "diploma"),
    ("high school", "high_school"),
    ("secondary", "high_school"),
]


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


def _normalize_education_level(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    raw_str = str(raw).strip().lower()
    normalized = raw_str.replace(" ", "_")
    if normalized in EDUCATION_LEVEL_VALUES:
        return normalized
    text = raw_str.replace("_", " ")
    for needle, mapped in EDUCATION_ALIASES:
        if needle in text:
            return mapped
    return None


def _age_from_dob(dob: Any) -> int | None:
    if not dob:
        return None
    try:
        parsed = datetime.strptime(str(dob)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    years = today.year - parsed.year
    if (today.month, today.day) < (parsed.month, parsed.day):
        years -= 1
    return years if years >= 0 else None


def _months_employed_from_resume(resume: dict[str, Any], experience_years: float) -> int | None:
    history = resume.get("employment_history")
    if isinstance(history, list) and history:
        return min(24, max(0, int(round(experience_years * 12))))
    if experience_years > 0:
        return min(24, int(round(min(experience_years, 2.0) * 12)))
    return None


def assemble_features(
    form_data: dict[str, Any], extractions: list[dict]
) -> tuple[dict[str, Any], list[str]]:
    """Return (features, provenance_notes)."""
    by_type = _extraction_by_type(extractions)
    notes: list[str] = []

    features: dict[str, Any] = {}
    for key, default in NUMERIC_DEFAULTS.items():
        features[key] = _to_float(form_data.get(key), default)
    for key, default in CATEGORICAL_DEFAULTS.items():
        features[key] = str(form_data.get(key) or default)

    eid = by_type.get("emirates_id", {})
    dob_age = _age_from_dob(eid.get("date_of_birth"))
    if dob_age is not None:
        raw_age = form_data.get("age")
        form_age_default = int(NUMERIC_DEFAULTS["age"])
        use_dob_age = (
            raw_age is None
            or raw_age == ""
            or int(_to_float(raw_age, form_age_default)) == form_age_default
        )
        if use_dob_age:
            features["age"] = dob_age
            notes.append(f"Age derived from Emirates ID date of birth ({dob_age}).")

    bank = by_type.get("bank_statement", {})
    bank_income = _to_float(bank.get("average_monthly_income"), 0.0)
    if bank_income > 0:
        if abs(bank_income - features["monthly_income"]) > 500:
            notes.append(
                f"Income adjusted to bank-statement value AED {bank_income:,.0f} "
                f"(form stated AED {features['monthly_income']:,.0f})."
            )
        features["monthly_income"] = bank_income

    credit = by_type.get("credit_report", {})
    credit_score = _to_float(credit.get("credit_score"), 0.0)
    if credit_score > 0:
        features["credit_score"] = credit_score
    elif "credit_report" not in by_type:
        features["credit_score"] = _to_float(form_data.get("credit_score"), 0.0)

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

    resume = by_type.get("resume", {})
    resume_years = _to_float(resume.get("total_experience_years"), 0.0)
    if resume_years > 0:
        features["employment_years"] = resume_years
        notes.append(f"Employment years taken from resume ({resume_years:.1f} years).")
        months = _months_employed_from_resume(resume, resume_years)
        if months is not None:
            features["months_employed_last_2yrs"] = months
            notes.append(
                f"Months employed (last 2 years) estimated from resume ({months} months)."
            )

    edu = _normalize_education_level(resume.get("education"))
    if edu:
        features["education_level"] = edu
        notes.append(f"Education level taken from resume ({edu}).")

    family_size = max(1.0, features["family_size"])
    features["income_per_capita"] = round(features["monthly_income"] / family_size, 2)

    return features, notes
