"""Quick integration check for login endpoint (backend must be running)."""
from __future__ import annotations

import os

import pytest
import requests

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"),
    reason="Set RUN_INTEGRATION_TESTS=1 with backend on localhost:8000",
)
def test_login_endpoint_live():
    response = requests.post(
        "http://localhost:8000/api/login",
        data={"username": "testuser", "password": "testpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=5,
    )
    assert response.status_code in (200, 401)
