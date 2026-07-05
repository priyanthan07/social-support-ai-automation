"""Validation cross-check tests."""

from app.agents.validation import _overlap


def test_address_overlap_detects_mismatch():
    assert _overlap("Villa 12, Al Wathba, Abu Dhabi", "Marina Heights, Dubai") < 0.3


def test_address_overlap_detects_match():
    assert _overlap("Villa 12, Al Wathba, Abu Dhabi", "Villa 12 Al Wathba Abu Dhabi") > 0.5
