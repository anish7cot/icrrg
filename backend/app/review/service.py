"""Code-review pipeline — orchestrates diff → prompt → LLM → validated findings.

Supports 4 reasoning levels:
  Level 1: Rule-based only (handled outside this module)
  Level 2: LLM with Chain-of-Thought reasoning
  Level 3: Cross-finding correlation (attack chains)
  Level 4: Risk synthesis and remediation roadmap
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from ..config import settings
from ..git.diff_parser import ParsedDiff, parse_unified_diff
from ..llm.base import TokenUsage, get_provider, ReviewFinding as LLMReviewFinding
from .correlation import CorrelationResult, run_correlation_analysis
from .dedup import deduplicate_findings
from .response_parser import ReviewFindingModel, parse_llm_response, validate_line_numbers
from .synthesis import SynthesisResult, run_synthesis

logger = logging.getLogger(__name__)

# Maximum total added lines before we chunk by file.
_MAX_LINES_PER_CALL = 3000
# Max concurrent LLM calls for chunked diffs.
_MAX_CONCURRENT_LLM = 3


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
    reasoning: str = ""  # Chain-of-thought (Level 2+)


@dataclass
class ReviewPipelineResult:
    """Complete output from the multi-level review pipeline."""
    findings: list[CodeReviewFinding] = field(default_factory=list)
    correlation: CorrelationResult | None = None
    synthesis: SynthesisResult | None = None
    total_usage: TokenUsage = field(default_factory=TokenUsage)
    llm_calls_count: int = 0
    llm_total_duration_ms: int = 0
    reasoning_level_executed: int = 1


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
        reasoning=f.reasoning,
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


def _aggregate_usage(base: TokenUsage, addition: TokenUsage) -> TokenUsage:
    """Accumulate token usage."""
    return TokenUsage(
        prompt_tokens=base.prompt_tokens + addition.prompt_tokens,
        completion_tokens=base.completion_tokens + addition.completion_tokens,
        total_tokens=base.total_tokens + addition.total_tokens,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_code_review(
    diff_text: str,
    reasoning_level: int | None = None,
) -> ReviewPipelineResult:
    """Full multi-level review pipeline.

    Args:
        diff_text: Raw unified diff text (should be sanitized before calling).
        reasoning_level: Override for reasoning depth (1-4). Defaults to settings.REASONING_LEVEL.

    Returns:
        ReviewPipelineResult with findings from all executed levels.
    """
    level = reasoning_level if reasoning_level is not None else settings.REASONING_LEVEL
    level = max(1, min(4, level))  # Clamp to 1-4

    result = ReviewPipelineResult(reasoning_level_executed=level)

    # Level 1 is handled outside (rule-based engines in scan API)
    if level < 2:
        return result

    # --- Level 2: LLM with Chain-of-Thought ---
    parsed = parse_unified_diff(diff_text)
    if not parsed.files:
        return result

    chunks = _chunk_diff(diff_text, parsed)
    valid_lines = _build_valid_lines(parsed)

    provider = get_provider()
    all_findings: list[ReviewFindingModel] = []

    # Process chunks with concurrency limit
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_LLM)

    async def _review_chunk(chunk: str) -> list[LLMReviewFinding]:
        async with semaphore:
            return await provider.review(chunk)

    if len(chunks) == 1:
        # Single chunk — direct call
        from ..review.prompts.system import build_review_prompt
        messages = build_review_prompt(chunks[0])
        response = await provider.chat(messages, temperature=0)
        result.total_usage = _aggregate_usage(result.total_usage, response.usage)
        result.llm_calls_count += 1
        result.llm_total_duration_ms += response.duration_ms

        # Parse findings from response
        llm_findings = response.findings
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
                    reasoning=lf.reasoning,
                )
                all_findings.append(model)
            except Exception as exc:
                logger.warning("Skipping invalid LLM finding: %s", exc)
    else:
        # Multiple chunks — parallel calls
        tasks = [_review_chunk(chunk) for chunk in chunks]
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        for chunk_findings in chunk_results:
            if isinstance(chunk_findings, Exception):
                logger.warning("Chunk review failed: %s", chunk_findings)
                continue
            result.llm_calls_count += 1
            for lf in chunk_findings:
                try:
                    model = ReviewFindingModel(
                        severity=lf.severity,
                        category=lf.category,
                        file=lf.file,
                        line=lf.line,
                        issue=lf.issue,
                        explanation=lf.explanation,
                        suggestion=lf.suggestion,
                        reasoning=lf.reasoning,
                    )
                    all_findings.append(model)
                except Exception as exc:
                    logger.warning("Skipping invalid LLM finding: %s", exc)

    # Validate line numbers
    all_findings = validate_line_numbers(all_findings, valid_lines)

    # Convert to unified format
    result.findings = [_finding_model_to_unified(f) for f in all_findings]

    if level < 3:
        return result

    # --- Level 3: Cross-Finding Correlation ---
    # Build findings dict list for correlation engine
    findings_for_correlation = [
        {
            "finding_type": f.rule_name,
            "severity": f.severity,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "message": f.description,
        }
        for f in result.findings
    ]

    if len(findings_for_correlation) >= 2:
        correlation_result = await run_correlation_analysis(findings_for_correlation)
        result.correlation = correlation_result
        result.total_usage = _aggregate_usage(result.total_usage, correlation_result.usage)
        result.llm_calls_count += 1
        result.llm_total_duration_ms += correlation_result.duration_ms

    if level < 4:
        return result

    # --- Level 4: Risk Synthesis ---
    correlations_data = []
    if result.correlation and result.correlation.chains:
        correlations_data = [
            {
                "chain_id": c.chain_id,
                "finding_refs": c.finding_refs,
                "combined_severity": c.combined_severity,
                "attack_narrative": c.attack_narrative,
            }
            for c in result.correlation.chains
        ]

    synthesis_result = await run_synthesis(findings_for_correlation, correlations_data)
    result.synthesis = synthesis_result
    result.total_usage = _aggregate_usage(result.total_usage, synthesis_result.usage)
    result.llm_calls_count += 1
    result.llm_total_duration_ms += synthesis_result.duration_ms

    return result
