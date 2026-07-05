"""Application use-case orchestration (create, upload, process, query)."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.agents.graph import run_pipeline
from app.core.config import settings
from app.core.enums import ApplicationStatus, DocumentType, PIPELINE_STAGES
from app.core.exceptions import AppError, NotFoundError, ProcessingError
from app.core.logging import get_logger
from app.repositories import application_repository as repo
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationSummary,
    DecisionResponse,
    DocumentInfo,
    ProcessResponse,
)

logger = get_logger(__name__)

ALLOWED_DOC_TYPES = {d.value for d in DocumentType}
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".pdf", ".xlsx", ".xls", ".csv",
}


def _ensure_upload_dir(application_id: uuid.UUID) -> Path:
    base = Path(settings.upload_dir) / str(application_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def create_application(db: Session, payload: ApplicationCreate):
    return repo.create_application(
        db,
        applicant_name=payload.applicant_name,
        form_data=payload.form_data,
        emirates_id=payload.emirates_id,
        email=payload.email,
        phone=payload.phone,
    )


def upload_document(
    db: Session,
    application_id: uuid.UUID,
    doc_type: str,
    file: UploadFile,
) -> DocumentInfo:
    if doc_type not in ALLOWED_DOC_TYPES:
        raise AppError(f"Invalid document type: {doc_type}")

    app = repo.get_application(db, application_id)
    if app is None:
        raise NotFoundError("Application not found")

    if app.status not in {ApplicationStatus.RECEIVED, ApplicationStatus.FAILED}:
        raise AppError("Documents can only be uploaded before processing starts.")

    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix and suffix not in ALLOWED_EXTENSIONS:
        raise AppError(f"Unsupported file extension: {suffix}")

    upload_dir = _ensure_upload_dir(application_id)
    safe_name = f"{doc_type}{suffix or '.bin'}"
    dest = upload_dir / safe_name

    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    doc = repo.add_document(
        db,
        application_id=application_id,
        doc_type=doc_type,
        filename=file.filename or safe_name,
        storage_path=str(dest),
    )
    return DocumentInfo.model_validate(doc)


def enqueue_processing(db: Session, application_id: uuid.UUID) -> ProcessResponse:
    app = repo.get_application(db, application_id)
    if app is None:
        raise NotFoundError("Application not found")

    if app.status in {
        ApplicationStatus.EXTRACTING,
        ApplicationStatus.VALIDATING,
        ApplicationStatus.SCORING,
        ApplicationStatus.RECOMMENDING,
    }:
        return ProcessResponse(
            application_id=application_id,
            status=app.status,
            message="Processing already in progress.",
            queued=False,
        )

    if app.status == ApplicationStatus.DECIDED:
        return ProcessResponse(
            application_id=application_id,
            status=app.status,
            message="Application already decided.",
            queued=False,
        )

    docs = repo.get_documents(db, application_id)
    if not docs:
        raise ProcessingError("Upload at least one document before processing.")

    if not repo.claim_for_processing(db, application_id):
        app = repo.get_application(db, application_id)
        status = app.status if app else ApplicationStatus.EXTRACTING
        return ProcessResponse(
            application_id=application_id,
            status=status,
            message="Processing already in progress.",
            queued=False,
        )

    repo.add_audit(
        db,
        application_id,
        stage=ApplicationStatus.EXTRACTING,
        message="Processing queued.",
    )

    return ProcessResponse(
        application_id=application_id,
        status=ApplicationStatus.EXTRACTING,
        message="Processing started in background.",
        queued=True,
    )


def run_processing_background(application_id: str) -> None:
    """Execute the LangGraph pipeline (intended for BackgroundTasks)."""
    try:
        run_pipeline(application_id)
    except Exception as exc:
        logger.exception("Background processing failed for %s", application_id)
        raise


def get_application_detail(db: Session, application_id: uuid.UUID) -> ApplicationDetail:
    app = repo.get_application(db, application_id)
    if app is None:
        raise NotFoundError("Application not found")

    decision = None
    if app.decision is not None:
        meta = app.decision.model_metadata or {}
        decision = DecisionResponse(
            outcome=app.decision.outcome,
            eligibility_probability=app.decision.eligibility_probability,
            support_amount=app.decision.support_amount,
            confidence=app.decision.confidence,
            auto_decision=app.decision.auto_decision,
            reasons=app.decision.reasons or [],
            validation_flags=app.decision.validation_flags or [],
            recommendations=app.decision.recommendations or [],
            narrative=meta.get("narrative"),
            validation_summary=meta.get("validation_summary"),
        )

    audit = [
        {
            "stage": a.stage,
            "message": a.message,
            "created_at": a.created_at.isoformat(),
            "payload": a.payload,
        }
        for a in repo.get_audit_log(db, application_id)
    ]

    return ApplicationDetail(
        id=app.id,
        status=app.status,
        applicant_name=app.applicant_name,
        emirates_id=app.emirates_id,
        email=app.email,
        phone=app.phone,
        form_data=app.form_data or {},
        error=app.error,
        created_at=app.created_at,
        updated_at=app.updated_at,
        documents=[DocumentInfo.model_validate(d) for d in app.documents],
        decision=decision,
        audit=audit,
    )


def list_applications(db: Session, limit: int = 100) -> list[ApplicationSummary]:
    apps = repo.list_applications(db, limit=limit)
    return [
        ApplicationSummary(
            id=a.id,
            status=a.status,
            applicant_name=a.applicant_name,
            created_at=a.created_at,
            outcome=a.decision.outcome if a.decision else None,
        )
        for a in apps
    ]


def progress_percent(status: str) -> int:
    if status == ApplicationStatus.FAILED:
        return 0
    if status in PIPELINE_STAGES:
        idx = PIPELINE_STAGES.index(status)
        return int((idx / (len(PIPELINE_STAGES) - 1)) * 100)
    return 0
