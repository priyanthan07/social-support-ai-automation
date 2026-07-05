"""Multimodal document extractors (image OCR, PDF, Excel) + LLM structuring."""

from app.extractors.service import extract_document
from app.extractors.base import ExtractionResult

__all__ = ["extract_document", "ExtractionResult"]
