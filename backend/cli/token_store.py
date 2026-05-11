"""Persistent token storage for CLI authentication.

Stores the JWT access token and refresh token in ~/.icrrg/ so the CLI
and hook can authenticate with the backend API.
"""

from __future__ import annotations

import json
from pathlib import Path

_TOKEN_DIR = Path.home() / ".icrrg"
_TOKEN_FILE = _TOKEN_DIR / "token"
_REFRESH_FILE = _TOKEN_DIR / "refresh_token"


def save_token(token: str, refresh_token: str | None = None) -> Path:
    """Save the JWT access token (and optionally refresh token) to disk."""
    _TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    _TOKEN_FILE.write_text(token, encoding="utf-8")
    if refresh_token:
        _REFRESH_FILE.write_text(refresh_token, encoding="utf-8")
    return _TOKEN_FILE


def load_token() -> str | None:
    """Load the stored JWT access token, or None if not logged in."""
    if _TOKEN_FILE.is_file():
        token = _TOKEN_FILE.read_text(encoding="utf-8").strip()
        return token if token else None
    return None


def load_refresh_token() -> str | None:
    """Load the stored refresh token, or None."""
    if _REFRESH_FILE.is_file():
        token = _REFRESH_FILE.read_text(encoding="utf-8").strip()
        return token if token else None
    return None


def clear_token() -> None:
    """Remove all stored tokens."""
    if _TOKEN_FILE.is_file():
        _TOKEN_FILE.unlink()
    if _REFRESH_FILE.is_file():
        _REFRESH_FILE.unlink()
