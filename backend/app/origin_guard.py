"""Block direct API abuse (cron/scripts) that bypass the Vercel frontend."""
import logging
import os
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("cineai.origin_guard")

_ENV = os.getenv("ENV", "production").lower()
_GUARD_ENABLED = os.getenv("REQUIRE_BROWSER_ORIGIN", "true").lower() in ("1", "true", "yes")

_DEFAULT_ORIGINS = "https://cineai-flame.vercel.app,http://localhost:5173,http://localhost:3000"
_origins_raw = os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS)
_ALLOWED_ORIGINS = {x.strip().rstrip("/") for x in _origins_raw.split(",") if x.strip()}

_EXEMPT_PREFIXES = (
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def _origin_allowed(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip().rstrip("/")
    if value in _ALLOWED_ORIGINS:
        return True
    try:
        parsed = urlparse(value)
        base = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        return base in _ALLOWED_ORIGINS
    except Exception:
        return False


def _has_auth_token(request: Request) -> bool:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer ") and len(auth.split(" ", 1)[-1].strip()) > 10:
        return True
    return bool(request.cookies.get("cineai_token"))


async def origin_guard_middleware(request: Request, call_next):
    if not _GUARD_ENABLED or _ENV != "production":
        return await call_next(request)

    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path or ""
    if path == "/" or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return await call_next(request)

    if not path.startswith("/api"):
        return await call_next(request)

    if _has_auth_token(request):
        return await call_next(request)

    # Set by our frontend fetch helper (Vercel rewrites may not forward Origin).
    if request.headers.get("x-cineai-client") == "1":
        return await call_next(request)

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    if _origin_allowed(origin) or _origin_allowed(referer):
        return await call_next(request)

    client = _rate_limit_key_safe(request)
    logger.warning("Blocked API request without allowed Origin (path=%s client=%s)", path, client)
    return JSONResponse(
        status_code=403,
        content={"detail": "Forbidden"},
    )


def _rate_limit_key_safe(request: Request) -> str:
    try:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
        if request.client is not None:
            return getattr(request.client, "host", None) or "unknown"
    except Exception:
        pass
    return "unknown"
