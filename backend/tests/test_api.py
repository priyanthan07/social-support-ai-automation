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


@patch("app.api.routes.health.postgres_ping", return_value=True)
@patch("app.api.routes.health.mongo.ping", return_value=True)
@patch("app.api.routes.health.qdrant.ping", return_value=True)
@patch("app.api.routes.health.neo4j.ping", return_value=True)
@patch("app.api.routes.health.get_model")
def test_health_ready_includes_postgres(
    mock_model, mock_neo4j, mock_qdrant, mock_mongo, mock_postgres, client
):
    mock_model.return_value.available = True
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["checks"]["postgres"] is True


@patch("app.api.routes.chat.mongo.get_chat_history", return_value=[{"role": "user", "content": "Hi"}])
def test_chat_history_endpoint(mock_history, client):
    app_id = uuid.uuid4()
    r = client.get(f"/chat/history/{app_id}")
    assert r.status_code == 200
    assert r.json()["turns"] == [{"role": "user", "content": "Hi"}]


@patch("app.api.routes.chat.answer_question", return_value="Hello there.")
def test_chat_post_endpoint(mock_answer, client):
    app_id = uuid.uuid4()
    r = client.post("/chat", json={"application_id": str(app_id), "message": "Hello?"})
    assert r.status_code == 200
    assert r.json()["answer"] == "Hello there."


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
