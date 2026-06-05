"""Rate limiter for API (slowapi). Shared by main and routes."""
import os

try:
    from jose import jwt
    from slowapi import Limiter

    _ENV = os.getenv("ENV", "production").lower()
    _SECRET = os.getenv("SECRET_KEY", "").strip() or "dev_secret_key"
    _DEFAULT_LIMIT = "60/minute" if _ENV != "production" else "40/minute"

    def _rate_limit_key(request):
        """Safe key for rate limiting; never raises (request.client can be None behind proxy)."""
        try:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip() or "unknown"
            if request.client is not None:
                return getattr(request.client, "host", None) or "unknown"
            return "unknown"
        except Exception:
            return "unknown"

    def rate_limit_user_or_ip(request):
        """Per-user bucket when Bearer/cookie token present; else IP."""
        token = None
        try:
            auth = request.headers.get("Authorization") or ""
            if auth.lower().startswith("bearer "):
                token = auth.split(" ", 1)[1].strip()
            if not token:
                token = request.cookies.get("cineai_token")
            if token:
                payload = jwt.decode(
                    token,
                    _SECRET,
                    algorithms=["HS256"],
                    options={"verify_exp": False},
                )
                sub = payload.get("sub")
                if sub:
                    return f"user:{sub}"
        except Exception:
            pass
        return _rate_limit_key(request)

    limiter = Limiter(key_func=_rate_limit_key, default_limits=[_DEFAULT_LIMIT])
    LIMITER_AVAILABLE = True
except ImportError:
    rate_limit_user_or_ip = None  # type: ignore

    class _DummyLimiter:
        def exempt(self, f):
            return f

        def limit(self, *args, **kwargs):
            return lambda f: f

    limiter = _DummyLimiter()
    LIMITER_AVAILABLE = False
