"""Shared enumerations for application status, document types, and outcomes."""

from __future__ import annotations

from enum import StrEnum


class ApplicationStatus(StrEnum):
    RECEIVED = "received"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    SCORING = "scoring"
    RECOMMENDING = "recommending"
    DECIDED = "decided"
    FAILED = "failed"


class DocumentType(StrEnum):
    EMIRATES_ID = "emirates_id"
    BANK_STATEMENT = "bank_statement"
    RESUME = "resume"
    ASSETS_LIABILITIES = "assets_liabilities"
    CREDIT_REPORT = "credit_report"
    OTHER = "other"


class DecisionOutcome(StrEnum):
    APPROVE = "approve"
    SOFT_DECLINE = "soft_decline"
    NEEDS_REVIEW = "needs_review"


# Ordered pipeline stages for UI progress rendering.
PIPELINE_STAGES: list[str] = [
    ApplicationStatus.RECEIVED,
    ApplicationStatus.EXTRACTING,
    ApplicationStatus.VALIDATING,
    ApplicationStatus.SCORING,
    ApplicationStatus.RECOMMENDING,
    ApplicationStatus.DECIDED,
]
