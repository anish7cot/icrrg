"""Persistent token storage for CLI authentication.

Stores the JWT token in ~/.icrrg/token so the CLI and hook can
authenticate with the backend API.
"""

from __future__ import annotations

from pathlib import Path

_TOKEN_DIR = Path.home() / ".icrrg"
_TOKEN_FILE = _TOKEN_DIR / "token"


def save_token(token: str) -> Path:
    """Save the JWT token to disk."""
    _TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    _TOKEN_FILE.write_text(token, encoding="utf-8")
    return _TOKEN_FILE


def load_token() -> str | None:
    """Load the stored JWT token, or None if not logged in."""
    if _TOKEN_FILE.is_file():
        token = _TOKEN_FILE.read_text(encoding="utf-8").strip()
        return token if token else None
    return None


def clear_token() -> None:
    """Remove the stored token."""
    if _TOKEN_FILE.is_file():
        _TOKEN_FILE.unlink()
