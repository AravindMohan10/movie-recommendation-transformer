"""Rate limiter for API (slowapi). Shared by main and routes. Optional: app runs without slowapi if not installed."""
try:
    from slowapi import Limiter

    def _rate_limit_key(request):
        """Safe key for rate limiting; never raises (request.client can be None behind proxy)."""
        try:
            if request.client is not None:
                return getattr(request.client, "host", None) or "unknown"
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip() or "unknown"
            return "unknown"
        except Exception:
            return "unknown"

    limiter = Limiter(key_func=_rate_limit_key, default_limits=["120/minute"])
    LIMITER_AVAILABLE = True
except ImportError:
    # No-op limiter when slowapi is not installed (e.g. moodenv without slowapi)
    class _DummyLimiter:
        def exempt(self, f):
            return f
        def limit(self, *args, **kwargs):
            return lambda f: f
    limiter = _DummyLimiter()
    LIMITER_AVAILABLE = False
