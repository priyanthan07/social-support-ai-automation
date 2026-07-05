"""PDF text + table extraction via pdfplumber."""

from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_pdf(path: str | Path) -> tuple[str, list[list]]:
    """Return (concatenated_text, list_of_tables)."""
    try:
        import pdfplumber

        texts: list[str] = []
        tables: list[list] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                texts.append(page.extract_text() or "")
                for table in page.extract_tables():
                    tables.append(table)
        return "\n".join(texts), tables
    except Exception as exc:  # pragma: no cover
        logger.warning("PDF extraction failed for %s: %s", path, exc)
        return "", []
