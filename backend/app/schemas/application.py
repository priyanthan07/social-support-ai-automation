"""Pydantic request/response schemas for the application API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ApplicationCreate(BaseModel):
    applicant_name: str = Field(..., min_length=2, max_length=255)
    emirates_id: str | None = None
    email: str | None = None
    phone: str | None = None
    form_data: dict[str, Any] = Field(default_factory=dict)


class DocumentInfo(BaseModel):
    id: UUID
    doc_type: str
    filename: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionResponse(BaseModel):
    outcome: str
    eligibility_probability: float | None = None
    support_amount: float = 0.0
    confidence: float | None = None
    auto_decision: bool = True
    reasons: list[str] = Field(default_factory=list)
    validation_flags: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    narrative: str | None = None
    validation_summary: str | None = None

    model_config = {"from_attributes": True}


class ApplicationSummary(BaseModel):
    id: UUID
    status: str
    applicant_name: str
    created_at: datetime
    outcome: str | None = None

    model_config = {"from_attributes": True}


class ApplicationDetail(BaseModel):
    id: UUID
    status: str
    applicant_name: str
    emirates_id: str | None = None
    email: str | None = None
    phone: str | None = None
    form_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentInfo] = Field(default_factory=list)
    decision: DecisionResponse | None = None
    audit: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProcessResponse(BaseModel):
    application_id: UUID
    status: str
    message: str
    queued: bool = False


class ChatRequest(BaseModel):
    application_id: UUID
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    application_id: UUID
    answer: str
