"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _test_env(monkeypatch, tmp_path):
    """Use isolated env for config tests."""
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("ML_ARTIFACTS_DIR", str(Path(__file__).resolve().parents[2] / "ml" / "artifacts"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    yield
