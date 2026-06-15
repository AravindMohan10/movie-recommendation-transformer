"""Sanity checks for rate limit constants."""
from __future__ import annotations

from backend.app import rate_limits


def test_rate_limit_constants_defined():
    for name in (
        "RECOMMENDATIONS",
        "HIDDEN_GEMS",
        "SURPRISE_ME",
        "LOGIN",
        "SIGNUP",
        "HEALTH",
    ):
        value = getattr(rate_limits, name)
        assert isinstance(value, str) and "/" in value
