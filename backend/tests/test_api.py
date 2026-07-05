"""API endpoint tests with mocked services."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@patch("app.api.routes.applications.svc.create_application")
@patch("app.api.routes.applications.svc.get_application_detail")
def test_create_application(mock_detail, mock_create, client):
    app_id = uuid.uuid4()
    mock_app = MagicMock()
    mock_app.id = app_id
    mock_create.return_value = mock_app
    mock_detail.return_value = {
        "id": str(app_id),
        "status": "received",
        "applicant_name": "Test User",
        "emirates_id": None,
        "email": None,
        "phone": None,
        "form_data": {},
        "error": None,
        "created_at": "2026-07-04T00:00:00+00:00",
        "updated_at": "2026-07-04T00:00:00+00:00",
        "documents": [],
        "decision": None,
        "audit": [],
    }
    payload = {"applicant_name": "Test User", "form_data": {"monthly_income": 5000}}
    r = client.post("/applications", json=payload)
    assert r.status_code == 201
