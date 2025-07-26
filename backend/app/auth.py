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
    """Bcrypt only uses first 72 bytes; truncate so long passwords don't raise."""
    if isinstance(password, bytes):
        password = password.decode("utf-8", errors="ignore")
    if not isinstance(password, str):
        password = str(password) if password is not None else ""
    b = password.encode("utf-8")[:72]
    return b.decode("utf-8", errors="ignore")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(truncate_password_for_bcrypt(plain_password), hashed_password)


def hash_password(plain_password: str | bytes) -> str:
    safe = truncate_password_for_bcrypt(plain_password)
    try:
        return pwd_context.hash(safe)
    except Exception as e:
        if "72 bytes" in str(e):
            # Fallback: force truncate and retry (handles any path where long password slipped through)
            if isinstance(plain_password, bytes):
                forced = plain_password[:72].decode("utf-8", errors="ignore")
            else:
                forced = (plain_password or "").encode("utf-8")[:72].decode("utf-8", errors="ignore")
            return pwd_context.hash(forced)
        raise

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)