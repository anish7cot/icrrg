"""Load blocking-policy config from an optional .icrrg.yml file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

# ── severity levels ordered from most to least severe ────────────────
SEVERITY_ORDER: list[str] = ["critical", "high", "medium", "low"]

# Valid actions for each severity
Action = Literal["block", "warn", "info"]


@dataclass
class BlockingPolicy:
    """Per-severity action table.

    Defaults (when no .icrrg.yml exists):
      critical → block
      high     → block
      medium   → warn
      low      → info
    """

    critical: Action = "block"
    high: Action = "block"
    medium: Action = "warn"
    low: Action = "info"

    def action_for(self, severity: str) -> Action:
        """Return the configured action for the given severity string."""
        return getattr(self, severity.lower(), "info")

    def is_blocking(self, severity: str) -> bool:
        return self.action_for(severity) == "block"

    def is_warn(self, severity: str) -> bool:
        return self.action_for(severity) == "warn"


_VALID_ACTIONS = {"block", "warn", "info"}


def load_config(repo_root: str | Path | None = None) -> BlockingPolicy:
    """Read `.icrrg.yml` from *repo_root* and return a `BlockingPolicy`.

    If the file doesn't exist or is malformed, return sensible defaults
    without raising — the tool should never break because of a config issue.
    """
    if repo_root is None:
        return BlockingPolicy()

    config_path = Path(repo_root) / ".icrrg.yml"
    if not config_path.is_file():
        return BlockingPolicy()

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception:
        return BlockingPolicy()

    if not isinstance(raw, dict):
        return BlockingPolicy()

    blocking_raw = raw.get("blocking") or raw  # top-level or nested under `blocking:`
    if not isinstance(blocking_raw, dict):
        return BlockingPolicy()

    policy = BlockingPolicy()
    for sev in SEVERITY_ORDER:
        val = blocking_raw.get(sev)
        if isinstance(val, str) and val.lower() in _VALID_ACTIONS:
            object.__setattr__(policy, sev, val.lower())

    return policy
