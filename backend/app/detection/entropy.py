"""Entropy-based secret detection engine.

Complements the regex engine by catching high-entropy strings that look
like randomly-generated secrets (API keys, tokens, passwords) but don't
match a known pattern.  Uses Shannon entropy with context filtering to
avoid flagging UUIDs, hashes, and normal base64 data.
"""

from __future__ import annotations

import math
import re
from pydantic import BaseModel

from app.git.diff_parser import ParsedDiff

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
HEX_ENTROPY_THRESHOLD = 4.5
BASE64_ENTROPY_THRESHOLD = 5.0
DEFAULT_ENTROPY_THRESHOLD = 4.8  # general-purpose fallback
MIN_SECRET_LENGTH = 16  # ignore short tokens

# Character-set detectors
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/=_\-]+$")

# ---------------------------------------------------------------------------
# Context: variable names that suggest a secret
# ---------------------------------------------------------------------------
_SECRET_VAR_RE = re.compile(
    r"(?i)\b(key|secret|token|password|passwd|pwd|api_key|api[_-]?secret|"
    r"access[_-]?key|private[_-]?key|auth[_-]?token|credentials?|conn(?:ection)?[_-]?str(?:ing)?)\b"
)

# ---------------------------------------------------------------------------
# Patterns to SKIP — UUIDs, common hashes, etc.
# ---------------------------------------------------------------------------
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_HASH_CONST_RE = re.compile(
    r"(?i)\b(sha256|sha1|sha512|md5|hash|digest|checksum)\b"
)
_IMPORT_RE = re.compile(r"^\s*(import|from|require|include)\b")
_COMMENT_RE = re.compile(r"^\s*(#|//|/?\*)")

# Paths to skip (mirrors regex_engine logic)
_SKIP_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\.example$"),
    re.compile(r"(?i)\.sample$"),
    re.compile(r"(?i)\.template$"),
    re.compile(r"(?i)(?:^|/)tests?/"),
    re.compile(r"(?i)_test\.\w+$"),
    re.compile(r"(?i)\.test\.\w+$"),
    re.compile(r"(?i)test_[^/]+\.\w+$"),
    re.compile(r"(?i)/fixtures?/"),
    re.compile(r"(?i)/mocks?/"),
    re.compile(r"(?i)\.md$"),
    re.compile(r"(?i)(?:^|/)eval/benchmarks?/"),  # evaluation benchmark data
]

# Regex to extract candidate strings: quoted strings or long unquoted tokens
_QUOTED_STR_RE = re.compile(r"""(['"])(?P<val>[^'"]{8,})\1""")
_UNQUOTED_TOKEN_RE = re.compile(r"=\s*(?P<val>[A-Za-z0-9_+/\-.]{16,})\s*$")


# ---------------------------------------------------------------------------
# Shannon entropy
# ---------------------------------------------------------------------------
def shannon_entropy(data: str) -> float:
    """Calculate the Shannon entropy of a string (bits per character)."""
    if not data:
        return 0.0
    length = len(data)
    freq: dict[str, int] = {}
    for ch in data:
        freq[ch] = freq.get(ch, 0) + 1
    return -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )


def _entropy_threshold(candidate: str) -> float:
    """Pick the right threshold based on the character set."""
    if _HEX_RE.match(candidate):
        return HEX_ENTROPY_THRESHOLD
    if _BASE64_RE.match(candidate):
        return BASE64_ENTROPY_THRESHOLD
    return DEFAULT_ENTROPY_THRESHOLD


def _redact(text: str) -> str:
    """Show first 4 and last 2 chars, mask the rest."""
    if len(text) <= 8:
        return text[:2] + "*" * (len(text) - 2)
    return text[:4] + "*" * (len(text) - 6) + text[-2:]


def _should_skip_path(path: str) -> bool:
    return any(p.search(path) for p in _SKIP_PATH_PATTERNS)


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------
class EntropyFinding(BaseModel):
    """A high-entropy string finding in the diff."""

    rule_name: str = "high-entropy-string"
    description: str
    severity: str = "medium"
    confidence: float
    file_path: str
    line_number: int
    matched_text: str   # redacted
    entropy_score: float
    line_content: str


# ---------------------------------------------------------------------------
# Extract candidate strings from a line
# ---------------------------------------------------------------------------
def _extract_candidates(line: str) -> list[str]:
    """Pull out quoted strings and long unquoted assignment values."""
    candidates: list[str] = []
    for m in _QUOTED_STR_RE.finditer(line):
        candidates.append(m.group("val"))
    m = _UNQUOTED_TOKEN_RE.search(line)
    if m:
        candidates.append(m.group("val"))
    return candidates


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def scan_diff_for_entropy(
    parsed_diff: ParsedDiff,
    *,
    skip_tests: bool = True,
    threshold_override: float | None = None,
) -> list[EntropyFinding]:
    """Scan a parsed diff for high-entropy strings in suspicious contexts.

    Args:
        parsed_diff: Output from ``parse_unified_diff()``.
        skip_tests:  Skip test / example files.
        threshold_override: Force a single entropy threshold for all strings.

    Returns:
        List of ``EntropyFinding`` objects.
    """
    findings: list[EntropyFinding] = []

    for file_diff in parsed_diff.files:
        file_path = file_diff.new_path or file_diff.old_path or "<unknown>"

        if file_diff.is_binary:
            continue
        if skip_tests and _should_skip_path(file_path):
            continue

        for diff_line in file_diff.added_lines:
            content = diff_line.content

            # Skip comments and imports
            if _COMMENT_RE.match(content) or _IMPORT_RE.match(content):
                continue

            # Context check: line must reference a secret-like variable name
            if not _SECRET_VAR_RE.search(content):
                continue

            # Skip lines that look like hash/checksum constants
            if _HASH_CONST_RE.search(content):
                continue

            # Skip lines containing UUIDs
            if _UUID_RE.search(content):
                continue

            for candidate in _extract_candidates(content):
                if len(candidate) < MIN_SECRET_LENGTH:
                    continue

                ent = shannon_entropy(candidate)
                threshold = threshold_override or _entropy_threshold(candidate)

                if ent >= threshold:
                    # Confidence scales with how far above threshold
                    confidence = min(0.95, 0.60 + (ent - threshold) * 0.15)
                    findings.append(
                        EntropyFinding(
                            description=f"High-entropy string (entropy={ent:.2f}) in secret context",
                            severity="medium",
                            confidence=round(confidence, 2),
                            file_path=file_path,
                            line_number=diff_line.line_number,
                            matched_text=_redact(candidate),
                            entropy_score=round(ent, 2),
                            line_content=content,
                        )
                    )

    return findings
