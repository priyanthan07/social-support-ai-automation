"""Load and serve the trained scikit-learn models at inference time.

Loads the calibrated classifier, the support-amount regressor, and metadata
produced by the offline ``ssa_ml.train`` job. Artifacts are read from the
directory configured by ``settings.ml_artifacts_dir`` (mounted into the
container). The runtime never trains -- it only loads and predicts.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelBundle:
    def __init__(self) -> None:
        base = Path(settings.ml_artifacts_dir)
        self.classifier_path = base / "eligibility_classifier.joblib"
        self.regressor_path = base / "support_amount_regressor.joblib"
        self.metadata_path = base / "model_metadata.json"
        self._classifier = None
        self._regressor = None
        self._metadata: dict[str, Any] | None = None

    @property
    def available(self) -> bool:
        return self.classifier_path.exists() and self.metadata_path.exists()

    @property
    def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            if self.metadata_path.exists():
                self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            else:
                self._metadata = {}
        return self._metadata

    def _load(self) -> None:
        import joblib

        if self._classifier is None:
            self._classifier = joblib.load(self.classifier_path)
        if self._regressor is None and self.regressor_path.exists():
            self._regressor = joblib.load(self.regressor_path)

    def _feature_frame(self, features: dict[str, Any]):
        import pandas as pd

        meta = self.metadata
        cols = meta.get("numeric_features", []) + meta.get("categorical_features", [])
        row = {c: features.get(c) for c in cols}
        return pd.DataFrame([row], columns=cols)

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """Return probability, support amount, and confidence for an applicant."""
        if not self.available:
            raise RuntimeError(
                "ML artifacts not found. Run `uv run python -m ssa_ml.train` first."
            )
        self._load()
        frame = self._feature_frame(features)
        proba = float(self._classifier.predict_proba(frame)[0, 1])

        support_amount = 0.0
        if self._regressor is not None:
            max_amt = self.metadata.get("max_support_amount", 15000.0)
            support_amount = float(min(max(self._regressor.predict(frame)[0], 0.0), max_amt))

        # Confidence = distance from the 0.5 boundary, scaled to [0, 1].
        confidence = round(min(1.0, abs(proba - 0.5) * 2), 4)
        return {
            "probability": round(proba, 4),
            "support_amount": round(support_amount, 2),
            "confidence": confidence,
        }

    def feature_importance(self, top_n: int = 8) -> dict[str, float]:
        imp = self.metadata.get("permutation_importance", {})
        return dict(list(imp.items())[:top_n])


@lru_cache
def get_model() -> ModelBundle:
    return ModelBundle()
