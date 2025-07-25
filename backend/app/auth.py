# backend/app/auth.py
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import os
from .models import User
from .database import get_db
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
_RAW_SECRET = os.getenv("SECRET_KEY", "").strip()
# In production, require explicit SECRET_KEY; never use dev default
_ENV = os.getenv("ENV", "development").lower()
if _ENV == "production":
    if not _RAW_SECRET or _RAW_SECRET == "dev_secret_key":
        raise RuntimeError(
            "Production requires SECRET_KEY to be set to a secure random value. "
            "Do not use dev_secret_key in production."
        )
SECRET_KEY = _RAW_SECRET if _RAW_SECRET else "dev_secret_key"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    # 1) check Authorization header
    auth_header: str | None = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]

    # 2) else fall back to cookie
    if not token:
        token = request.cookies.get("cineai_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3) decode & validate
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.user_id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def truncate_password_for_bcrypt(password: str | bytes) -> str:
    """Truncate password to 72 bytes. Only used for verify_password (backward compat with existing hashes)."""
    if isinstance(password, bytes):
        password = password.decode("utf-8", errors="ignore")
    if not isinstance(password, str):
        password = str(password) if password is not None else ""
    b = password.encode("utf-8")[:72]
    return b.decode("utf-8", errors="ignore")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Truncate for backward compatibility (existing users may have passwords that were truncated)
    return pwd_context.verify(truncate_password_for_bcrypt(plain_password), hashed_password)


def hash_password(plain_password: str | bytes) -> str:
    """Hash password. Password should already be validated (<=72 bytes) by schema."""
    if isinstance(plain_password, bytes):
        plain_password = plain_password.decode("utf-8", errors="ignore")
    if not isinstance(plain_password, str):
        plain_password = str(plain_password) if plain_password is not None else ""
    
    # Defensive check: if somehow >72 bytes, raise instead of truncating
    byte_length = len(plain_password.encode("utf-8"))
    if byte_length > 72:
        raise ValueError(
            f"Password is too long ({byte_length} bytes). Maximum 72 bytes. "
            "This should have been caught by validation."
        )
    
    return pwd_context.hash(plain_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)