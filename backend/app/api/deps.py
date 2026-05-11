"""FastAPI dependency — extract & validate the current user from JWT."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import decode_access_token
from app.db.models.user import User
from app.db.models.user_project import UserProject
from app.db.session import get_session

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token_data = decode_access_token(creds.credentials)
    if token_data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    username = token_data["username"]
    result = await session.execute(select(User).where(User.username == username, User.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Like get_current_user but returns None instead of raising — for endpoints
    that work both authenticated and unauthenticated (e.g. the scan POST from CLI)."""
    if creds is None:
        return None
    token_data = decode_access_token(creds.credentials)
    if token_data is None:
        return None
    username = token_data["username"]
    result = await session.execute(select(User).where(User.username == username, User.is_active == True))  # noqa: E712
    return result.scalar_one_or_none()


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires the user to have admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_manager_or_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires manager or admin role."""
    if user.role not in ("admin", "manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin access required")
    return user


async def get_user_repos(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Return the list of repositories the current user is allowed to access."""
    result = await session.execute(
        select(UserProject.repository).where(UserProject.user_id == user.id)
    )
    return [row[0] for row in result.all()]


async def ensure_user_project(
    user_id, repository: str, session: AsyncSession
) -> None:
    """Link a user to a repository if not already linked."""
    existing = await session.execute(
        select(UserProject.id).where(
            UserProject.user_id == user_id,
            UserProject.repository == repository,
        )
    )
    if not existing.scalar_one_or_none():
        session.add(UserProject(user_id=user_id, repository=repository))
