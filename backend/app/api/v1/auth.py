"""POST /api/v1/auth/register — create user.
POST /api/v1/auth/login    — obtain JWT + refresh token.
POST /api/v1/auth/refresh  — rotate refresh token.
POST /api/v1/auth/logout   — revoke refresh token.
GET  /api/v1/auth/me       — current user info.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.api.deps import get_current_user
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    role: str = "developer"


class UserResponse(BaseModel):
    username: str
    is_active: bool
    role: str


def _validate_password_strength(password: str) -> None:
    """Enforce strong password policy."""
    errors: list[str] = []
    if not re.search(r"[A-Z]", password):
        errors.append("must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;':\",./<>?]", password):
        errors.append("must contain at least one special character")
    if errors:
        raise HTTPException(
            status_code=422,
            detail=f"Password {', '.join(errors)}",
        )


async def _issue_tokens(
    user: User, session: AsyncSession
) -> TokenResponse:
    """Create access + refresh tokens for a user."""
    access_token = create_access_token(user.username, user.role)
    raw_refresh, refresh_hash = generate_refresh_token()

    rt = RefreshToken(
        token_hash=refresh_hash,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(rt)
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        username=user.username,
        role=user.role,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    _validate_password_strength(body.password)

    existing = await session.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(username=body.username, hashed_password=hash_password(body.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return await _issue_tokens(user, session)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        # Increment failed attempts if user exists
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=LOCKOUT_DURATION_MINUTES
                )
            await session.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Check lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=423,
            detail="Account temporarily locked due to too many failed login attempts",
        )

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    await session.commit()

    return await _issue_tokens(user, session)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    token_hash = hash_refresh_token(body.refresh_token)
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    rt = result.scalar_one_or_none()
    if rt is None or rt.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Revoke old token (rotation)
    rt.revoked = True

    # Load user
    user_result = await session.execute(
        select(User).where(User.id == rt.user_id, User.is_active == True)  # noqa: E712
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        await session.commit()
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return await _issue_tokens(user, session)


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    """Revoke a refresh token."""
    token_hash = hash_refresh_token(body.refresh_token)
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(revoked=True)
    )
    await session.commit()


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(username=user.username, is_active=user.is_active, role=user.role)
