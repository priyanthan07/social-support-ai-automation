# Social Support AI - ML training project

Offline project that:

1. Generates a **pure synthetic** labeled applicant dataset with realistic
   distributions, correlations, injected noise, and borderline cases
   (`ssa_ml.generate_data`).
2. Also renders **sample applicant documents** (Emirates ID image, bank
   statement / credit report / resume PDFs, assets-liabilities Excel) for the
   end-to-end demo (`ssa_ml.generate_documents`).
3. Trains and evaluates the scikit-learn decision models
   (`ssa_ml.train`): a `HistGradientBoostingClassifier` (primary), a
   `LogisticRegression` interpretable baseline, and a
   `HistGradientBoostingRegressor` for the suggested support amount.

Artifacts are written to `ml/artifacts/` and mounted read-only into the
backend container.

```bash
uv sync
uv run python -m ssa_ml.generate_data
uv run python -m ssa_ml.train
uv run python -m ssa_ml.generate_documents   # optional demo documents
```
