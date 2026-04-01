"""Lightweight diff-hash cache for skipping redundant scans (e.g. amend)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _cache_file(repo_root: str | Path) -> Path:
    """Return the path to the cache file inside .git/."""
    return Path(repo_root) / ".git" / "securediff_cache.json"


def _hash_diff(diff_text: str) -> str:
    return hashlib.sha256(diff_text.encode("utf-8")).hexdigest()


def check_cache(repo_root: str | Path | None, diff_text: str) -> bool | None:
    """Return cached exit-code-is-zero (True=clean, False=blocked) or None."""
    if repo_root is None:
        return None
    cf = _cache_file(repo_root)
    if not cf.is_file():
        return None
    try:
        data = json.loads(cf.read_text(encoding="utf-8"))
    except Exception:
        return None
    diff_hash = _hash_diff(diff_text)
    if data.get("diff_hash") == diff_hash:
        return data.get("clean", None)
    return None


def write_cache(repo_root: str | Path | None, diff_text: str, clean: bool) -> None:
    """Persist the scan result keyed by diff hash."""
    if repo_root is None:
        return
    cf = _cache_file(repo_root)
    try:
        cf.write_text(
            json.dumps({"diff_hash": _hash_diff(diff_text), "clean": clean}),
            encoding="utf-8",
        )
    except OSError:
        pass  # non-critical — caching is best-effort
