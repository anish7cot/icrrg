"""JWT + password hashing utilities."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Short-lived access token
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, role: str = "developer") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Return {username, role} dict or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        if payload.get("type") != "access":
            return None
        return {"username": sub, "role": payload.get("role", "developer")}
    except JWTError:
        return None


def generate_refresh_token() -> tuple[str, str]:
    """Return (raw_token, token_hash) pair."""
    raw = secrets.token_urlsafe(48)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    """Hash a raw refresh token for DB lookup."""
    return hashlib.sha256(raw.encode()).hexdigest()
