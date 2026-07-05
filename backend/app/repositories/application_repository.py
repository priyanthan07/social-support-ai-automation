"""Data-access layer for applications, documents, decisions, and audit log.

Contains no business logic -- only persistence operations against PostgreSQL.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ApplicationStatus
from app.models.entities import Application, AuditLog, Decision, Document


def create_application(
    db: Session,
    applicant_name: str,
    form_data: dict[str, Any],
    emirates_id: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> Application:
    app = Application(
        applicant_name=applicant_name,
        form_data=form_data,
        emirates_id=emirates_id,
        email=email,
        phone=phone,
        status=ApplicationStatus.RECEIVED,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def get_application(db: Session, application_id: uuid.UUID) -> Application | None:
    stmt = (
        select(Application)
        .options(selectinload(Application.documents), selectinload(Application.decision))
        .where(Application.id == application_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_applications(db: Session, limit: int = 100) -> list[Application]:
    stmt = (
        select(Application)
        .options(selectinload(Application.decision))
        .order_by(Application.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def update_status(
    db: Session,
    application_id: uuid.UUID,
    status: str,
    error: str | None = None,
    *,
    clear_error: bool = False,
) -> None:
    app = db.get(Application, application_id)
    if app is None:
        return
    app.status = status
    if clear_error:
        app.error = None
    elif error is not None:
        app.error = error
    db.commit()


def claim_for_processing(db: Session, application_id: uuid.UUID) -> bool:
    """Atomically transition received/failed -> extracting. Returns True if claimed."""
    result = db.execute(
        update(Application)
        .where(
            Application.id == application_id,
            Application.status.in_(
                [ApplicationStatus.RECEIVED, ApplicationStatus.FAILED]
            ),
        )
        .values(status=ApplicationStatus.EXTRACTING, error=None)
    )
    db.commit()
    return result.rowcount == 1


def upsert_document(
    db: Session,
    application_id: uuid.UUID,
    doc_type: str,
    filename: str,
    storage_path: str,
) -> Document:
    """Insert or replace the document row for (application_id, doc_type)."""
    existing = db.execute(
        select(Document).where(
            Document.application_id == application_id,
            Document.doc_type == doc_type,
        )
    ).scalar_one_or_none()
    if existing:
        existing.filename = filename
        existing.storage_path = storage_path
        existing.mongo_id = None
        db.commit()
        db.refresh(existing)
        return existing
    doc = Document(
        application_id=application_id,
        doc_type=doc_type,
        filename=filename,
        storage_path=storage_path,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def add_document(
    db: Session,
    application_id: uuid.UUID,
    doc_type: str,
    filename: str,
    storage_path: str,
) -> Document:
    return upsert_document(db, application_id, doc_type, filename, storage_path)


def set_document_mongo_id(db: Session, document_id: uuid.UUID, mongo_id: str) -> None:
    doc = db.get(Document, document_id)
    if doc:
        doc.mongo_id = mongo_id
        db.commit()


def get_documents(db: Session, application_id: uuid.UUID) -> list[Document]:
    stmt = select(Document).where(Document.application_id == application_id)
    return list(db.execute(stmt).scalars().all())


def save_decision(db: Session, application_id: uuid.UUID, **fields: Any) -> Decision:
    """Insert or replace the decision for an application."""
    existing = db.execute(
        select(Decision).where(Decision.application_id == application_id)
    ).scalar_one_or_none()
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    decision = Decision(application_id=application_id, **fields)
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def add_audit(
    db: Session,
    application_id: uuid.UUID | None,
    stage: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(AuditLog(application_id=application_id, stage=stage, message=message, payload=payload))
    db.commit()


def get_audit_log(db: Session, application_id: uuid.UUID) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.application_id == application_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())
