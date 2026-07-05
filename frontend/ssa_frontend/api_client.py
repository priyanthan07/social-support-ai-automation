"""HTTP client for the FastAPI backend."""

from __future__ import annotations

from typing import Any

import requests

from ssa_frontend.config import get_settings


class ApiClient:
    def __init__(self, base_url: str | None = None, timeout: int = 120) -> None:
        self.base_url = (base_url or get_settings().backend_api_url).rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def health(self) -> dict[str, Any]:
        r = requests.get(self._url("/health"), timeout=10)
        r.raise_for_status()
        return r.json()

    def create_application(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = requests.post(self._url("/applications"), json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_applications(self, limit: int = 100) -> list[dict[str, Any]]:
        r = requests.get(self._url("/applications"), params={"limit": limit}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_application(self, application_id: str) -> dict[str, Any]:
        r = requests.get(self._url(f"/applications/{application_id}"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def upload_document(self, application_id: str, doc_type: str, file_bytes: bytes, filename: str) -> dict[str, Any]:
        files = {"file": (filename, file_bytes)}
        data = {"doc_type": doc_type}
        r = requests.post(
            self._url(f"/applications/{application_id}/documents"),
            files=files,
            data=data,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def process_application(self, application_id: str) -> dict[str, Any]:
        r = requests.post(self._url(f"/applications/{application_id}/process"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def chat(self, application_id: str, message: str) -> dict[str, Any]:
        r = requests.post(
            self._url("/chat"),
            json={"application_id": application_id, "message": message},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def get_chat_history(self, application_id: str, limit: int = 50) -> list[dict[str, str]]:
        r = requests.get(
            self._url(f"/chat/history/{application_id}"),
            params={"limit": limit},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json().get("turns", [])
