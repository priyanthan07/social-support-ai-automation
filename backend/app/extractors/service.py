"""Unified document extraction entrypoint.

Routes each document to the correct modality handler (image OCR, PDF, Excel),
then structures free-text documents into normalized JSON via the LLM.
"""

from __future__ import annotations

from pathlib import Path

from app.core.enums import DocumentType
from app.extractors.base import ExtractionResult
from app.extractors.excel import extract_assets_liabilities
from app.extractors.llm_structuring import structure_fields
from app.extractors.ocr import IMAGE_EXTENSIONS, ocr_image
from app.extractors.pdf import extract_pdf


def extract_document(
    doc_type: str, path: str | Path, config: dict | None = None
) -> ExtractionResult:
    """Extract raw content and structured fields from a single document."""
    path = Path(path)
    ext = path.suffix.lower()

    # --- Tabular: assets & liabilities (deterministic, no LLM) ---
    if doc_type == DocumentType.ASSETS_LIABILITIES or ext in {".xlsx", ".xls", ".csv"}:
        structured = extract_assets_liabilities(path)
        return ExtractionResult(
            doc_type=doc_type,
            raw_text="",
            structured=structured,
            modality="tabular",
        )

    # --- Image: OCR then LLM structuring ---
    if doc_type == DocumentType.EMIRATES_ID or ext in IMAGE_EXTENSIONS:
        raw_text = ocr_image(path)
        structured = structure_fields(doc_type, raw_text, config=config)
        return ExtractionResult(
            doc_type=doc_type,
            raw_text=raw_text,
            structured=structured,
            modality="image",
        )

    # --- PDF / text: pdfplumber then LLM structuring ---
    if ext == ".pdf":
        raw_text, tables = extract_pdf(path)
    else:
        raw_text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""

    structured = structure_fields(doc_type, raw_text, config=config)
    return ExtractionResult(
        doc_type=doc_type,
        raw_text=raw_text,
        structured=structured,
        modality="text",
    )
