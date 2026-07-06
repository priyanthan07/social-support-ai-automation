"""Train + evaluate the eligibility models and persist artifacts.

Run:  uv run python -m ssa_ml.train

Produces (in ml/artifacts/):
    eligibility_classifier.joblib        - calibrated HistGradientBoosting pipeline
    eligibility_baseline_logreg.joblib   - interpretable LogisticRegression baseline
    support_amount_regressor.joblib      - HistGradientBoosting regressor
    model_metadata.json                  - schema, metrics, permutation importances
    feature_importance.png               - explainability plot
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    r2_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ssa_ml import paths
from ssa_ml.schema import (
    CATEGORICAL_FEATURES,
    CATEGORY_VALUES,
    MAX_SUPPORT_AMOUNT,
    NUMERIC_FEATURES,
    POVERTY_LINE_PER_CAPITA,
)

REVIEW_BAND = (0.40, 0.60)  # probability band flagged as low-confidence (human review)


def _build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def _train_test_split(df: pd.DataFrame, seed: int = 42):
    from sklearn.model_selection import train_test_split

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df["eligible"]
    return train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)


def train() -> dict:
    paths.ensure_dirs()
    df = pd.read_csv(paths.DATASET_CSV)

    X_train, X_test, y_train, y_test = _train_test_split(df)

    # --- Primary model: calibrated gradient boosting ---
    gb_pipeline = Pipeline(
        steps=[
            ("prep", _build_preprocessor()),
            ("clf", HistGradientBoostingClassifier(random_state=42, max_iter=300)),
        ]
    )
    classifier = CalibratedClassifierCV(gb_pipeline, method="isotonic", cv=3)
    classifier.fit(X_train, y_train)

    # --- Interpretable baseline: logistic regression ---
    baseline = Pipeline(
        steps=[
            ("prep", _build_preprocessor()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    baseline.fit(X_train, y_train)

    # --- Evaluate classifiers ---
    def _eval(model) -> dict:
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)
        return {
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
            "f1": round(float(f1_score(y_test, pred)), 4),
            "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        }

    gb_metrics = _eval(classifier)
    baseline_metrics = _eval(baseline)
    report = classification_report(
        y_test, (classifier.predict_proba(X_test)[:, 1] >= 0.5).astype(int), output_dict=True
    )

    # --- Support-amount regressor (trained on eligible applicants) ---
    elig = df[df["eligible"] == 1]
    Xr = elig[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    yr = elig["support_amount"]
    from sklearn.model_selection import train_test_split

    Xr_tr, Xr_te, yr_tr, yr_te = train_test_split(Xr, yr, test_size=0.2, random_state=42)
    regressor = Pipeline(
        steps=[
            ("prep", _build_preprocessor()),
            ("reg", HistGradientBoostingRegressor(random_state=42, max_iter=300)),
        ]
    )
    regressor.fit(Xr_tr, yr_tr)
    yr_pred = np.clip(regressor.predict(Xr_te), 0, MAX_SUPPORT_AMOUNT)
    regressor_metrics = {
        "mae": round(float(mean_absolute_error(yr_te, yr_pred)), 2),
        "r2": round(float(r2_score(yr_te, yr_pred)), 4),
    }

    # --- Explainability: permutation importance (original feature names) ---
    perm = permutation_importance(
        classifier, X_test, y_test, n_repeats=8, random_state=42, scoring="roc_auc"
    )
    feature_names = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    importances = {
        name: round(float(val), 5)
        for name, val in sorted(
            zip(feature_names, perm.importances_mean), key=lambda kv: kv[1], reverse=True
        )
    }
    _plot_importances(importances)

    # --- Persist artifacts ---
    joblib.dump(classifier, paths.CLASSIFIER_PATH)
    joblib.dump(baseline, paths.BASELINE_PATH)
    joblib.dump(regressor, paths.REGRESSOR_PATH)

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "n_samples": int(len(df)),
        "approval_rate": round(float(df["eligible"].mean()), 4),
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "category_values": CATEGORY_VALUES,
        "decision_threshold": 0.5,
        "review_band": list(REVIEW_BAND),
        "poverty_line_per_capita": POVERTY_LINE_PER_CAPITA,
        "max_support_amount": MAX_SUPPORT_AMOUNT,
        "models": {
            "primary": "CalibratedClassifierCV(HistGradientBoostingClassifier)",
            "baseline": "LogisticRegression",
            "regressor": "HistGradientBoostingRegressor",
        },
        "metrics": {
            "classifier": gb_metrics,
            "baseline_logreg": baseline_metrics,
            "regressor": regressor_metrics,
            "classification_report": report,
        },
        "permutation_importance": importances,
    }
    paths.METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("=== Training complete ===")
    print(f"Classifier   ROC-AUC={gb_metrics['roc_auc']}  ACC={gb_metrics['accuracy']}  F1={gb_metrics['f1']}")
    print(f"Baseline     ROC-AUC={baseline_metrics['roc_auc']}  ACC={baseline_metrics['accuracy']}")
    print(f"Regressor    MAE={regressor_metrics['mae']}  R2={regressor_metrics['r2']}")
    print(f"Artifacts -> {paths.ARTIFACTS_DIR}")
    return metadata


def _plot_importances(importances: dict[str, float]) -> None:
    names = list(importances.keys())[:12][::-1]
    vals = [importances[n] for n in names]
    plt.figure(figsize=(8, 6))
    plt.barh(names, vals, color="#2563eb")
    plt.xlabel("Permutation importance (drop in ROC-AUC)")
    plt.title("Eligibility model - feature importance")
    plt.tight_layout()
    plt.savefig(paths.IMPORTANCE_PLOT_PATH, dpi=120)
    plt.close()


if __name__ == "__main__":
    train()
