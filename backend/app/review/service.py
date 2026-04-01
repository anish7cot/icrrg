"""Code-review pipeline — orchestrates diff → prompt → LLM → validated findings."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..git.diff_parser import ParsedDiff, parse_unified_diff
from ..llm.base import get_provider, ReviewFinding as LLMReviewFinding
from .response_parser import ReviewFindingModel, parse_llm_response, validate_line_numbers

logger = logging.getLogger(__name__)

# Maximum total added lines before we chunk by file.
_MAX_LINES_PER_CALL = 3000


# ---------------------------------------------------------------------------
# Unified finding format (same shape as secret / entropy / PHI findings)
# ---------------------------------------------------------------------------

@dataclass
class CodeReviewFinding:
    """Single code-review finding in the unified format used by the scan API."""

    rule_name: str       # e.g. "llm:Injection"
    severity: str        # critical | high | medium | low
    description: str     # one-line issue summary
    explanation: str     # why it's a risk
    suggestion: str      # remediation advice
    file_path: str
    line_number: int
    confidence: float
    matched_text: str    # kept for compat — we use the issue text
    approximate_line: bool = False


def _finding_model_to_unified(f: ReviewFindingModel) -> CodeReviewFinding:
    return CodeReviewFinding(
        rule_name=f"llm:{f.category}",
        severity=f.severity.value,
        description=f.issue,
        explanation=f.explanation,
        suggestion=f.suggestion,
        file_path=f.file,
        line_number=f.line,
        confidence=0.85 if not f.approximate_line else 0.60,
        matched_text=f.issue,
        approximate_line=f.approximate_line,
    )


# ---------------------------------------------------------------------------
# Diff chunking for large diffs
# ---------------------------------------------------------------------------

def _rebuild_file_diff_text(parsed: ParsedDiff, file_idx: int) -> str:
    """Rebuild a minimal unified diff string for a single file."""
    f = parsed.files[file_idx]
    lines: list[str] = []
    lines.append(f"--- a/{f.old_path or f.new_path}")
    lines.append(f"+++ b/{f.new_path or f.old_path}")
    for dl in f.lines:
        prefix = "+" if dl.change_type == "add" else "-"
        lines.append(f"{prefix}{dl.content}")
    return "\n".join(lines)


def _chunk_diff(diff_text: str, parsed: ParsedDiff) -> list[str]:
    """Split a large diff into per-file chunks if it exceeds the line limit."""
    if parsed.total_additions + parsed.total_deletions <= _MAX_LINES_PER_CALL:
        return [diff_text]

    chunks: list[str] = []
    for i in range(len(parsed.files)):
        chunk = _rebuild_file_diff_text(parsed, i)
        if chunk.strip():
            chunks.append(chunk)
    return chunks or [diff_text]


# ---------------------------------------------------------------------------
# Valid line map for validation
# ---------------------------------------------------------------------------

def _build_valid_lines(parsed: ParsedDiff) -> dict[str, set[int]]:
    """Build file → set[added line numbers] from parsed diff."""
    result: dict[str, set[int]] = {}
    for f in parsed.files:
        path = f.new_path or f.old_path or ""
        result[path] = {dl.line_number for dl in f.added_lines}
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_code_review(diff_text: str) -> list[CodeReviewFinding]:
    """Full review pipeline: parse → chunk → LLM → validate → unify.

    Returns an empty list (not an exception) on total failure so the
    scan API can continue with rule-based findings.
    """
    # 1. Parse diff
    parsed = parse_unified_diff(diff_text)
    if not parsed.files:
        return []

    # 2. Chunk if needed
    chunks = _chunk_diff(diff_text, parsed)
    valid_lines = _build_valid_lines(parsed)

    # 3. Call LLM for each chunk
    provider = get_provider()
    all_findings: list[ReviewFindingModel] = []

    for chunk in chunks:
        llm_findings: list[LLMReviewFinding] = await provider.review(chunk)

        if not llm_findings:
            continue

        # Convert LLM dataclass findings → validated Pydantic models
        for lf in llm_findings:
            try:
                model = ReviewFindingModel(
                    severity=lf.severity,
                    category=lf.category,
                    file=lf.file,
                    line=lf.line,
                    issue=lf.issue,
                    explanation=lf.explanation,
                    suggestion=lf.suggestion,
                )
                all_findings.append(model)
            except Exception as exc:
                logger.warning("Skipping invalid LLM finding: %s", exc)

    # 4. Validate line numbers
    all_findings = validate_line_numbers(all_findings, valid_lines)

    # 5. Convert to unified format
    return [_finding_model_to_unified(f) for f in all_findings]
