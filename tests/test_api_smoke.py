"""FastAPI smoke tests (no running server required)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_root_and_health():
    client = TestClient(app)
    root = client.get("/")
    assert root.status_code == 200
    assert root.json().get("version")

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json().get("status") == "healthy"
