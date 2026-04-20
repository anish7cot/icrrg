"""Regex-based secret detection engine.

Scans ParsedDiff output from the diff parser, applies the secret-detection
rules, and returns structured findings.  Includes context-aware filtering
to suppress false positives in test files, example configs, and comments.
"""

from __future__ import annotations

import re
from pydantic import BaseModel

from app.git.diff_parser import DiffLine, FileDiff, ParsedDiff
from app.detection.rules.secrets import SECRET_RULES, SecretRule

# ---------------------------------------------------------------------------
# Paths / patterns to skip (false-positive suppression)
# ---------------------------------------------------------------------------
_SKIP_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\.example$"),          # .env.example, config.example
    re.compile(r"(?i)\.sample$"),           # .env.sample
    re.compile(r"(?i)\.template$"),         # config.template
    re.compile(r"(?i)(?:^|/)tests?/"),     # test directories
    re.compile(r"(?i)_test\.\w+$"),         # *_test.py, *_test.js
    re.compile(r"(?i)\.test\.\w+$"),        # *.test.ts
    re.compile(r"(?i)test_[^/]+\.\w+$"),   # test_*.py
    re.compile(r"(?i)/fixtures?/"),         # test fixtures
    re.compile(r"(?i)/mocks?/"),            # mocks
    re.compile(r"(?i)\.md$"),              # documentation files
    re.compile(r"(?i)(?:^|/)eval/benchmarks?/"),  # evaluation benchmark data
]

# Line-level patterns that suggest a comment or placeholder
_SKIP_LINE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*#"),                    # Python / shell comment
    re.compile(r"^\s*//"),                   # JS / TS / Go comment
    re.compile(r"^\s*/?\*"),                 # C-style block comment
    re.compile(r"(?i)\bplaceholder\b|\bchangeme\b|\byour[_-]?key\b|\bxxxx+\b"),
]


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------
class SecretFinding(BaseModel):
    """A single secret detected in the diff."""

    rule_name: str
    description: str
    severity: str          # critical / high / medium / low
    confidence: float      # 0-1
    file_path: str
    line_number: int
    matched_text: str      # redacted version of the match
    line_content: str      # full line content for context


def _redact(text: str) -> str:
    """Show first 4 and last 2 chars, mask the rest."""
    if len(text) <= 8:
        return text[:2] + "*" * (len(text) - 2)
    return text[:4] + "*" * (len(text) - 6) + text[-2:]


def _should_skip_path(path: str) -> bool:
    """Return True if the file path suggests a test/example file."""
    return any(p.search(path) for p in _SKIP_PATH_PATTERNS)


def _should_skip_line(content: str) -> bool:
    """Return True if the line looks like a comment or placeholder."""
    return any(p.search(content) for p in _SKIP_LINE_PATTERNS)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def scan_diff_for_secrets(
    parsed_diff: ParsedDiff,
    *,
    skip_tests: bool = True,
    rules: list[SecretRule] | None = None,
) -> list[SecretFinding]:
    """Scan a parsed diff for secrets using regex rules.

    Args:
        parsed_diff: Output from ``parse_unified_diff()``.
        skip_tests:  When True, suppress findings in test/example files.
        rules:       Override rule list (defaults to SECRET_RULES).

    Returns:
        A list of ``SecretFinding`` objects, one per match.
    """
    active_rules = rules if rules is not None else SECRET_RULES
    findings: list[SecretFinding] = []

    for file_diff in parsed_diff.files:
        file_path = file_diff.new_path or file_diff.old_path or "<unknown>"

        # Skip binary files
        if file_diff.is_binary:
            continue

        # Skip test / example files when requested
        if skip_tests and _should_skip_path(file_path):
            continue

        # Only scan added lines (new code entering the repo)
        for diff_line in file_diff.added_lines:
            # Skip comment / placeholder lines
            if _should_skip_line(diff_line.content):
                continue

            for rule in active_rules:
                match = rule.pattern.search(diff_line.content)
                if match:
                    secret_text = match.group("secret") if "secret" in match.groupdict() else match.group(0)
                    findings.append(
                        SecretFinding(
                            rule_name=rule.name,
                            description=rule.description,
                            severity=rule.severity,
                            confidence=rule.confidence,
                            file_path=file_path,
                            line_number=diff_line.line_number,
                            matched_text=_redact(secret_text),
                            line_content=diff_line.content,
                        )
                    )

    return findings
