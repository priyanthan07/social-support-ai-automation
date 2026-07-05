"""Shared extraction data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    """Result of extracting a single document."""

    doc_type: str
    raw_text: str = ""
    structured: dict[str, Any] = field(default_factory=dict)
    modality: str = "text"  # text | image | tabular
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "doc_type": self.doc_type,
            "raw_text": self.raw_text[:20000],
            "structured": self.structured,
            "modality": self.modality,
            "error": self.error,
        }
