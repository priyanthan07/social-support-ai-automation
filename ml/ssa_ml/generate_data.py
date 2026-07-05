"""Generate a pure-synthetic, realistically-distributed labeled dataset.

Run:  uv run python -m ssa_ml.generate_data
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from ssa_ml import paths
from ssa_ml.rules import label_dataset
from ssa_ml.schema import CATEGORY_VALUES

RANDOM_SEED = 42


def _sample_categorical(rng: np.random.Generator, values: list[str], probs: list[float], n: int) -> np.ndarray:
    return rng.choice(values, size=n, p=probs)


def generate(n: int = 12000, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    employment_status = _sample_categorical(
        rng,
        CATEGORY_VALUES["employment_status"],
        [0.48, 0.14, 0.22, 0.08, 0.08],
        n,
    )
    age = rng.integers(21, 66, size=n)
    family_size = np.clip(rng.poisson(3.2, size=n) + 1, 1, 10)
    num_dependents = np.array(
        [rng.integers(0, max(1, fs)) for fs in family_size]
    )

    # Income depends on employment status (monthly AED), lognormal-ish.
    base_income = np.select(
        [
            employment_status == "employed",
            employment_status == "self_employed",
            employment_status == "unemployed",
            employment_status == "retired",
            employment_status == "student",
        ],
        [
            rng.lognormal(mean=9.3, sigma=0.5, size=n),
            rng.lognormal(mean=9.1, sigma=0.7, size=n),
            rng.uniform(0, 2500, size=n),
            rng.uniform(2000, 9000, size=n),
            rng.uniform(0, 3500, size=n),
        ],
    )
    monthly_income = np.clip(base_income, 0, 80000).round(-1)
    income_per_capita = (monthly_income / family_size).round(2)

    employment_years = np.where(
        np.isin(employment_status, ["unemployed", "student"]),
        rng.uniform(0, 2, size=n),
        rng.uniform(0, 30, size=n),
    ).round(1)
    months_employed_last_2yrs = np.where(
        employment_status == "unemployed",
        rng.integers(0, 8, size=n),
        rng.integers(8, 25, size=n),
    )

    # Wealth: assets & liabilities correlated with income.
    total_assets = np.clip(
        monthly_income * rng.uniform(4, 40, size=n) + rng.uniform(0, 200000, size=n),
        0,
        5_000_000,
    ).round(-2)
    total_liabilities = np.clip(
        total_assets * rng.uniform(0.0, 0.8, size=n),
        0,
        4_000_000,
    ).round(-2)
    net_worth = (total_assets - total_liabilities).round(-2)

    credit_score = np.clip(rng.normal(640, 90, size=n), 300, 850).astype(int)

    housing_status = _sample_categorical(
        rng, CATEGORY_VALUES["housing_status"], [0.18, 0.42, 0.28, 0.12], n
    )
    education_level = _sample_categorical(
        rng, CATEGORY_VALUES["education_level"], [0.08, 0.32, 0.22, 0.30, 0.08], n
    )
    marital_status = _sample_categorical(
        rng, CATEGORY_VALUES["marital_status"], [0.34, 0.50, 0.10, 0.06], n
    )
    nationality_group = _sample_categorical(
        rng, CATEGORY_VALUES["nationality_group"], [0.35, 0.65], n
    )
    has_disability = _sample_categorical(rng, CATEGORY_VALUES["has_disability"], [0.09, 0.91], n)

    df = pd.DataFrame(
        {
            "monthly_income": monthly_income,
            "income_per_capita": income_per_capita,
            "family_size": family_size,
            "num_dependents": num_dependents,
            "age": age,
            "employment_years": employment_years,
            "months_employed_last_2yrs": months_employed_last_2yrs,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
            "credit_score": credit_score,
            "employment_status": employment_status,
            "housing_status": housing_status,
            "education_level": education_level,
            "marital_status": marital_status,
            "nationality_group": nationality_group,
            "has_disability": has_disability,
        }
    )

    df = label_dataset(df, rng)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic applicant dataset")
    parser.add_argument("--n", type=int, default=12000, help="number of applicants")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    paths.ensure_dirs()
    df = generate(n=args.n, seed=args.seed)
    df.to_csv(paths.DATASET_CSV, index=False)

    approval_rate = df["eligible"].mean()
    print(f"Wrote {len(df):,} rows -> {paths.DATASET_CSV}")
    print(f"Approval rate: {approval_rate:.1%}")
    print(
        "Avg support (eligible): "
        f"AED {df.loc[df.eligible == 1, 'support_amount'].mean():,.0f}/month"
    )


if __name__ == "__main__":
    main()
