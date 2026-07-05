"""Shared text comparison helpers for validation."""

from __future__ import annotations

import re


def normalize_tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    tokens = re.split(r"[\s,./-]+", str(text).lower())
    return {t for t in tokens if len(t) > 2}


def text_overlap(a: str | None, b: str | None) -> float:
    ta, tb = normalize_tokens(a), normalize_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
