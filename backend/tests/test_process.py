"""Processing endpoint and eligibility doc-gate tests."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.eligibility import _present_doc_types
from app.core.enums import ApplicationStatus
from app.main import app
from app.schemas.application import ProcessResponse


def test_present_doc_types_excludes_failed_and_empty():
    extractions = [
        {"doc_type": "emirates_id", "structured": {}, "error": "ocr failed"},
        {"doc_type": "resume", "structured": {}},
        {"doc_type": "bank_statement", "structured": {"average_monthly_income": 5000}},
    ]
    assert _present_doc_types(extractions) == {"bank_statement"}


@patch("app.api.routes.applications.svc.run_processing_background")
@patch("app.api.routes.applications.svc.enqueue_processing")
def test_process_queues_background_when_claimed(mock_enqueue, mock_run):
    client = TestClient(app)
    app_id = uuid.uuid4()
    mock_enqueue.return_value = ProcessResponse(
        application_id=app_id,
        status=ApplicationStatus.EXTRACTING,
        message="Processing started in background.",
        queued=True,
    )
    r = client.post(f"/applications/{app_id}/process")
    assert r.status_code == 200
    assert r.json()["queued"] is True
    mock_run.assert_called_once_with(str(app_id))


@patch("app.api.routes.applications.svc.run_processing_background")
@patch("app.api.routes.applications.svc.enqueue_processing")
def test_process_skips_background_when_not_queued(mock_enqueue, mock_run):
    client = TestClient(app)
    app_id = uuid.uuid4()
    mock_enqueue.return_value = ProcessResponse(
        application_id=app_id,
        status=ApplicationStatus.DECIDED,
        message="Application already decided.",
        queued=False,
    )
    r = client.post(f"/applications/{app_id}/process")
    assert r.status_code == 200
    assert r.json()["queued"] is False
    mock_run.assert_not_called()
