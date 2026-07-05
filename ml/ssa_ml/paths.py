"""Filesystem paths for the ML project (repo-root relative)."""

from __future__ import annotations

from pathlib import Path

# ml/ssa_ml/paths.py -> parents[2] == repository root
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = REPO_ROOT / "data" / "synthetic"
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
DOCUMENTS_DIR = DATA_DIR / "documents"
KB_DIR = REPO_ROOT / "data" / "knowledge_base"

DATASET_CSV = DATA_DIR / "applicants.csv"

# Trained model artifacts
CLASSIFIER_PATH = ARTIFACTS_DIR / "eligibility_classifier.joblib"
BASELINE_PATH = ARTIFACTS_DIR / "eligibility_baseline_logreg.joblib"
REGRESSOR_PATH = ARTIFACTS_DIR / "support_amount_regressor.joblib"
METADATA_PATH = ARTIFACTS_DIR / "model_metadata.json"
IMPORTANCE_PLOT_PATH = ARTIFACTS_DIR / "feature_importance.png"


def ensure_dirs() -> None:
    for d in (DATA_DIR, ARTIFACTS_DIR, DOCUMENTS_DIR, KB_DIR):
        d.mkdir(parents=True, exist_ok=True)
