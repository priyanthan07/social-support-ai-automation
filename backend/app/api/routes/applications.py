"""Application intake, document upload, processing, and status endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationSummary,
    ProcessResponse,
)
from app.services import application_service as svc

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationDetail, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    app = svc.create_application(db, payload)
    return svc.get_application_detail(db, app.id)


@router.get("", response_model=list[ApplicationSummary])
def list_applications(limit: int = 100, db: Session = Depends(get_db)):
    return svc.list_applications(db, limit=limit)


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(application_id: uuid.UUID, db: Session = Depends(get_db)):
    return svc.get_application_detail(db, application_id)


@router.post("/{application_id}/documents", response_model=ApplicationDetail)
def upload_document(
    application_id: uuid.UUID,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    svc.upload_document(db, application_id, doc_type, file)
    return svc.get_application_detail(db, application_id)


@router.post("/{application_id}/process", response_model=ProcessResponse)
def process_application(
    application_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    response = svc.enqueue_processing(db, application_id)
    if response.queued:
        background_tasks.add_task(svc.run_processing_background, str(application_id))
    return response
