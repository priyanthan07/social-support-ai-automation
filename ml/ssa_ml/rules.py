"""Documented ground-truth logic for generating synthetic labels.

This encodes a *defensible, transparent* notion of "need" used only to LABEL
the synthetic dataset. The trained model then learns this relationship (plus
injected noise), which is why held-out metrics are strong but not a suspicious
1.0. The runtime hard policy gates live separately in the backend
(`app/ml/rules.py`); this module is training-only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ssa_ml.schema import (
    MAX_SUPPORT_AMOUNT,
    MIN_SUPPORT_AMOUNT,
    POVERTY_LINE_PER_CAPITA,
)

_EMPLOYMENT_NEED = {
    "unemployed": 1.00,
    "student": 0.60,
    "retired": 0.55,
    "self_employed": 0.30,
    "employed": 0.15,
}


def compute_need_score(df: pd.DataFrame) -> pd.Series:
    """Latent need score (higher = more need). Roughly in [-0.35, 1.1]."""
    income_gap = (
        (POVERTY_LINE_PER_CAPITA - df["income_per_capita"]).clip(lower=0)
        / POVERTY_LINE_PER_CAPITA
    )
    dependents = (df["num_dependents"] / 6.0).clip(0, 1)
    employment = df["employment_status"].map(_EMPLOYMENT_NEED).fillna(0.3)
    wealth = (df["net_worth"] / 1_000_000.0).clip(0, 1)
    disability = (df["has_disability"] == "yes").astype(float) * 0.30
    credit_stress = ((650 - df["credit_score"]).clip(lower=0) / 350.0) * 0.20

    need = (
        0.45 * income_gap
        + 0.20 * dependents
        + 0.25 * employment
        + disability
        + credit_stress
        - 0.35 * wealth
    )
    return need


def label_dataset(df: pd.DataFrame, rng: np.random.Generator, threshold: float = 0.30) -> pd.DataFrame:
    """Attach ``need_score``, ``eligible`` and ``support_amount`` columns.

    Gaussian noise is added to the decision boundary so the problem is
    realistically imperfect (borderline cases get misclassified sometimes).
    """
    out = df.copy()
    need = compute_need_score(out)
    noise = rng.normal(0.0, 0.10, size=len(out))
    out["need_score"] = need
    out["eligible"] = ((need + noise) > threshold).astype(int)

    # Suggested monthly support for eligible applicants.
    poverty_target = POVERTY_LINE_PER_CAPITA * out["family_size"]
    gap = (poverty_target - out["monthly_income"]).clip(lower=0)
    raw_amount = 0.50 * gap + 1500.0 * need.clip(lower=0)
    amount = raw_amount.clip(MIN_SUPPORT_AMOUNT, MAX_SUPPORT_AMOUNT)
    out["support_amount"] = np.where(out["eligible"] == 1, amount.round(-1), 0.0)
    return out
