"""Excel / CSV tabular extraction for the assets & liabilities file.

Totals are computed deterministically (no LLM) for reliability, expecting the
columns: Category, Item, Type, Value_AED. Falls back to a best-effort numeric
sum if the schema differs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_assets_liabilities(path: str | Path) -> dict[str, Any]:
    try:
        import pandas as pd

        path = Path(path)
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

        df.columns = [str(c).strip().lower() for c in df.columns]
        value_col = next((c for c in df.columns if "value" in c or "amount" in c), None)
        type_col = next((c for c in df.columns if "type" in c or "category" in c), None)

        items: list[dict[str, Any]] = df.to_dict(orient="records")
        total_assets = 0.0
        total_liabilities = 0.0

        if value_col and type_col:
            for _, row in df.iterrows():
                kind = str(row[type_col]).strip().lower()
                try:
                    value = float(row[value_col])
                except (ValueError, TypeError):
                    continue
                if "asset" in kind:
                    total_assets += value
                elif "liab" in kind:
                    total_liabilities += value
        elif value_col:
            total_assets = float(pd.to_numeric(df[value_col], errors="coerce").fillna(0).sum())

        return {
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "net_worth": round(total_assets - total_liabilities, 2),
            "items": items,
        }
    except Exception as exc:  # pragma: no cover
        logger.warning("Excel extraction failed for %s: %s", path, exc)
        return {"total_assets": 0.0, "total_liabilities": 0.0, "net_worth": 0.0, "items": []}
