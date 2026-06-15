"""Unit tests for password hashing and JWT helpers."""
from __future__ import annotations

from jose import jwt

from backend.app.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify_roundtrip():
    hashed = hash_password("letmein")
    assert verify_password("letmein", hashed)
    assert not verify_password("wrong", hashed)


def test_create_access_token_decodes_with_sub():
    token = create_access_token({"sub": "42"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "42"
    assert "exp" in payload
