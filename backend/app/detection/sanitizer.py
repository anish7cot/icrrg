"""Diff sanitization layer — redacts secrets and PII before sending to external LLMs.

Runs the same detection patterns used by the regex, entropy, and NER engines
against every line of the raw diff text (added, removed, and context lines)
and replaces matched sensitive values with ``[REDACTED-<type>]`` placeholders.

This ensures the LLM receives enough structural context for a meaningful
code review without ever seeing real credentials or PII.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.detection.rules.secrets import SECRET_RULES
from app.detection.entropy import (
    MIN_SECRET_LENGTH,
    _BASE64_RE,
    _COMMENT_RE,
    _HASH_CONST_RE,
    _HEX_RE,
    _IMPORT_RE,
    _QUOTED_STR_RE,
    _SECRET_VAR_RE,
    _UNQUOTED_TOKEN_RE,
    _UUID_RE,
    shannon_entropy,
)
from app.detection.ner_pipeline import (
    _HEALTHCARE_KEYWORDS,
    _PHI_RULES,
    _nlp,
)

# ---------------------------------------------------------------------------
# Internal types
# ---------------------------------------------------------------------------

@dataclass
class _Span:
    """A region within a line to redact."""
    start: int
    end: int
    label: str  # "secret", "entropy", or "phi"


# ---------------------------------------------------------------------------
# Span collectors — find sensitive byte ranges per line
# ---------------------------------------------------------------------------

def _collect_secret_spans(line: str) -> list[_Span]:
    """Run secret-detection regex rules and return match spans."""
    spans: list[_Span] = []
    for rule in SECRET_RULES:
        for match in rule.pattern.finditer(line):
            if "secret" in match.groupdict():
                s, e = match.span("secret")
            else:
                s, e = match.span()
            spans.append(_Span(s, e, "secret"))
    return spans


def _entropy_threshold(candidate: str) -> float:
    if _HEX_RE.match(candidate):
        return 4.5
    if _BASE64_RE.match(candidate):
        return 5.0
    return 4.8


def _collect_entropy_spans(line: str) -> list[_Span]:
    """Find high-entropy strings in secret-like assignment contexts."""
    # Same pre-filters as entropy engine (minus path checks — handled by caller)
    if _COMMENT_RE.match(line) or _IMPORT_RE.match(line):
        return []
    if not _SECRET_VAR_RE.search(line):
        return []
    if _HASH_CONST_RE.search(line):
        return []
    if _UUID_RE.search(line):
        return []

    spans: list[_Span] = []

    for m in _QUOTED_STR_RE.finditer(line):
        candidate = m.group("val")
        if len(candidate) < MIN_SECRET_LENGTH:
            continue
        if shannon_entropy(candidate) >= _entropy_threshold(candidate):
            s, e = m.span("val")
            spans.append(_Span(s, e, "entropy"))

    m = _UNQUOTED_TOKEN_RE.search(line)
    if m:
        candidate = m.group("val")
        if len(candidate) >= MIN_SECRET_LENGTH:
            if shannon_entropy(candidate) >= _entropy_threshold(candidate):
                s, e = m.span("val")
                spans.append(_Span(s, e, "entropy"))

    return spans


def _collect_phi_spans(line: str, context_text: str) -> list[_Span]:
    """Find PHI (SSN, phone, MRN, DOB, person names) spans in a line."""
    spans: list[_Span] = []

    for rule in _PHI_RULES:
        for match in rule.pattern.finditer(line):
            if rule.needs_context and not _HEALTHCARE_KEYWORDS.search(context_text):
                continue
            s, e = match.span("phi")
            spans.append(_Span(s, e, "phi"))

    # spaCy NER for person names in healthcare context
    if _HEALTHCARE_KEYWORDS.search(context_text):
        doc = _nlp(line)
        for ent in doc.ents:
            if ent.label_ == "PERSON" and len(ent.text.strip()) >= 4:
                spans.append(_Span(ent.start_char, ent.end_char, "phi"))

    return spans


# ---------------------------------------------------------------------------
# Merge overlapping spans
# ---------------------------------------------------------------------------

def _merge_spans(spans: list[_Span]) -> list[_Span]:
    """Merge overlapping or adjacent spans, keeping the broadest label."""
    if not spans:
        return []
    # Sort by start offset, then by end descending (wider first)
    spans.sort(key=lambda s: (s.start, -s.end))
    merged: list[_Span] = [spans[0]]
    for span in spans[1:]:
        prev = merged[-1]
        if span.start <= prev.end:
            # Overlapping — extend
            if span.end > prev.end:
                prev.end = span.end
        else:
            merged.append(span)
    return merged


# ---------------------------------------------------------------------------
# Apply redactions to a single line
# ---------------------------------------------------------------------------

def _redact_line(line: str, spans: list[_Span]) -> str:
    """Replace spans in *line* with ``[REDACTED-<label>]``, right-to-left."""
    merged = _merge_spans(spans)
    # Process right-to-left so earlier offsets remain valid
    for span in reversed(merged):
        placeholder = f"[REDACTED-{span.label}]"
        line = line[:span.start] + placeholder + line[span.end:]
    return line


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitize_diff(diff_text: str) -> str:
    """Return a copy of *diff_text* with secrets and PII replaced by placeholders.

    Scans **all** diff lines (added, removed, and context) so that no
    sensitive value reaches the external LLM regardless of its diff status.
    """
    raw_lines = diff_text.split("\n")
    sanitized: list[str] = []

    # Build a small context window for NER healthcare checks.
    # We use surrounding raw lines (±3) as context.
    for i, raw_line in enumerate(raw_lines):
        # Determine the actual content to scan.
        # Diff lines start with +, -, or space; headers start with @@, diff, ---, +++
        # We only scan content lines (prefixed +, -, or space) — not diff metadata.
        if raw_line.startswith(("diff ", "--- ", "+++ ", "index ", "@@ ",
                                "old mode", "new mode", "rename ", "copy ",
                                "similarity", "dissimilarity",
                                "\\ No newline")):
            sanitized.append(raw_line)
            continue

        # Extract the content portion (after the +/- /space prefix)
        if raw_line.startswith(("+", "-", " ")):
            prefix = raw_line[0]
            content = raw_line[1:]
        else:
            # Not a standard diff line — pass through unchanged
            sanitized.append(raw_line)
            continue

        # Collect all sensitive spans in the content
        spans: list[_Span] = []
        spans.extend(_collect_secret_spans(content))
        spans.extend(_collect_entropy_spans(content))

        # Build a small context window for PHI healthcare checks
        context_start = max(0, i - 3)
        context_end = min(len(raw_lines), i + 4)
        context_text = " ".join(raw_lines[context_start:context_end])
        spans.extend(_collect_phi_spans(content, context_text))

        if spans:
            content = _redact_line(content, spans)

        sanitized.append(prefix + content)

    return "\n".join(sanitized)
