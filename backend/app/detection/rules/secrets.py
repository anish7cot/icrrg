"""Secret-detection regex rules.

Each rule is a dict with:
  - name:       human-readable identifier
  - pattern:    compiled regex (applied per-line)
  - severity:   "critical" | "high" | "medium" | "low"
  - confidence: float 0-1  (baseline; engine may adjust)
  - description: short explanation shown in findings
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretRule:
    name: str
    pattern: re.Pattern[str]
    severity: str
    confidence: float
    description: str


SECRET_RULES: list[SecretRule] = [
    # ── AWS ────────────────────────────────────────────────────────────
    SecretRule(
        name="aws-access-key-id",
        pattern=re.compile(r"(?:^|['\"\s=:])(?P<secret>AKIA[0-9A-Z]{16})\b"),
        severity="critical",
        confidence=0.95,
        description="AWS Access Key ID detected",
    ),
    SecretRule(
        name="aws-secret-access-key",
        pattern=re.compile(
            r"(?i)(?:aws_secret_access_key|aws_secret_key)\s*[=:]\s*['\"]?(?P<secret>[A-Za-z0-9/+=]{40})['\"]?"
        ),
        severity="critical",
        confidence=0.90,
        description="AWS Secret Access Key detected",
    ),
    # ── Private keys ──────────────────────────────────────────────────
    SecretRule(
        name="private-key-header",
        pattern=re.compile(r"(?P<secret>-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)"),
        severity="critical",
        confidence=0.99,
        description="Private key header detected",
    ),
    # ── Generic API keys / tokens ─────────────────────────────────────
    SecretRule(
        name="generic-api-key",
        pattern=re.compile(
            r"(?i)(?:api[_-]?key|api[_-]?token|access[_-]?token)\s*[=:]\s*['\"](?P<secret>[a-zA-Z0-9_\-]{20,})['\"]"
        ),
        severity="high",
        confidence=0.80,
        description="Generic API key / token assignment detected",
    ),
    SecretRule(
        name="bearer-token",
        pattern=re.compile(
            r"(?i)(?:authorization|bearer)\s*[=:]\s*['\"]?Bearer\s+(?P<secret>[A-Za-z0-9_\-.]{20,})['\"]?"
        ),
        severity="high",
        confidence=0.80,
        description="Bearer token detected",
    ),
    # ── Passwords / secrets in assignments ────────────────────────────
    SecretRule(
        name="password-assignment",
        pattern=re.compile(
            r"(?i)(?:password|passwd|pwd|secret|credentials)\s*[=:]\s*['\"](?P<secret>[^'\"]{4,})['\"]"
        ),
        severity="high",
        confidence=0.85,
        description="Hardcoded password or secret detected",
    ),
    # ── Connection strings with embedded password ─────────────────────
    SecretRule(
        name="connection-string-password",
        pattern=re.compile(
            r"(?i)(?:mysql|postgres(?:ql)?|mongodb(?:\+srv)?|redis|amqp|mssql)://[^:]+:(?P<secret>[^@\s]{4,})@"
        ),
        severity="high",
        confidence=0.85,
        description="Connection string with embedded password detected",
    ),
    # ── GitHub / GitLab tokens ────────────────────────────────────────
    SecretRule(
        name="github-token",
        pattern=re.compile(r"(?P<secret>gh[pousr]_[A-Za-z0-9_]{36,})"),
        severity="critical",
        confidence=0.95,
        description="GitHub personal access token detected",
    ),
    SecretRule(
        name="gitlab-token",
        pattern=re.compile(r"(?P<secret>glpat-[A-Za-z0-9_\-]{20,})"),
        severity="critical",
        confidence=0.95,
        description="GitLab personal access token detected",
    ),
    # ── Slack / Webhook tokens ────────────────────────────────────────
    SecretRule(
        name="slack-token",
        pattern=re.compile(r"(?P<secret>xox[baprs]-[0-9]{10,}-[A-Za-z0-9\-]+)"),
        severity="high",
        confidence=0.90,
        description="Slack token detected",
    ),
]
