"""Unit tests for API origin / client abuse guard."""
from __future__ import annotations

import pytest
from starlette.requests import Request

from backend.app.origin_guard import (
    _has_auth_token,
    _origin_allowed,
    origin_guard_middleware,
)


def _request(path: str, headers: dict | None = None) -> Request:
    raw = []
    for key, value in (headers or {}).items():
        raw.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_origin_allowed_exact_and_referer_base():
    assert _origin_allowed("https://cineai-flame.vercel.app")
    assert _origin_allowed("https://cineai-flame.vercel.app/dashboard")
    assert not _origin_allowed("https://evil.example.com")


def test_has_auth_token_bearer_and_cookie():
    assert _has_auth_token(_request("/api/x", {"Authorization": "Bearer " + "x" * 20}))
    assert _has_auth_token(_request("/api/x", {"Cookie": "cineai_token=abc12345678901"}))
    assert not _has_auth_token(_request("/api/x"))


@pytest.mark.asyncio
async def test_origin_guard_blocks_anonymous_api_in_production(monkeypatch):
    monkeypatch.setattr("backend.app.origin_guard._ENV", "production")
    monkeypatch.setattr("backend.app.origin_guard._GUARD_ENABLED", True)

    async def call_next(_request):
        raise AssertionError("should not reach app")

    req = _request("/api/movies/genres")
    resp = await origin_guard_middleware(req, call_next)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_origin_guard_allows_client_header(monkeypatch):
    monkeypatch.setattr("backend.app.origin_guard._ENV", "production")
    monkeypatch.setattr("backend.app.origin_guard._GUARD_ENABLED", True)

    async def call_next(_request):
        from starlette.responses import Response

        return Response("ok", status_code=200)

    req = _request("/api/movies/genres", {"X-CineAI-Client": "1"})
    resp = await origin_guard_middleware(req, call_next)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_origin_guard_exempts_health(monkeypatch):
    monkeypatch.setattr("backend.app.origin_guard._ENV", "production")
    monkeypatch.setattr("backend.app.origin_guard._GUARD_ENABLED", True)

    async def call_next(_request):
        from starlette.responses import Response

        return Response("ok", status_code=200)

    req = _request("/health")
    resp = await origin_guard_middleware(req, call_next)
    assert resp.status_code == 200
