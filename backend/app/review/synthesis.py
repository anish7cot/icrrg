"""Level 4 — Risk synthesis and remediation roadmap.

Produces a prioritized remediation plan by synthesizing all
findings and correlations from Levels 1-3.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from ..llm.base import TokenUsage, get_provider
from .prompts.synthesis import build_synthesis_prompt

logger = logging.getLogger(__name__)


@dataclass
class RemediationItem:
    """Single prioritized remediation action."""
    priority: int
    finding_refs: list[int]
    action: str
    effort: str  # low | medium | high
    impact: str  # low | medium | high


@dataclass
class SynthesisResult:
    """Output of Level 4 risk synthesis."""
    overall_risk_rating: str
    executive_summary: str
    remediation_priority: list[RemediationItem]
    architectural_recommendations: list[str]
    usage: TokenUsage
    duration_ms: int


async def run_synthesis(
    findings: list[dict],
    correlations: list[dict],
) -> SynthesisResult:
    """Run Level 4 risk synthesis and remediation roadmap.

    Args:
        findings: List of finding dicts from Levels 1+2
        correlations: List of correlation chain dicts from Level 3

    Returns:
        SynthesisResult with prioritized roadmap and token usage.
    """
    if not findings:
        return SynthesisResult(
            overall_risk_rating="minimal",
            executive_summary="No security findings detected.",
            remediation_priority=[],
            architectural_recommendations=[],
            usage=TokenUsage(),
            duration_ms=0,
        )

    # Prepare context
    findings_for_prompt = [
        {
            "index": i,
            "severity": f.get("severity", ""),
            "category": f.get("finding_type", ""),
            "file": f.get("file_path", ""),
            "line": f.get("line_number", 0),
            "issue": f.get("message", ""),
        }
        for i, f in enumerate(findings)
    ]

    findings_json = json.dumps(findings_for_prompt, indent=2)
    correlations_json = json.dumps(correlations, indent=2) if correlations else "[]"

    messages = build_synthesis_prompt(findings_json, correlations_json)

    provider = get_provider()
    try:
        content, usage, duration_ms = await provider.chat_raw(messages, temperature=0.1)
    except AttributeError:
        response = await provider.chat(messages, temperature=0.1)
        content = ""
        usage = response.usage
        duration_ms = response.duration_ms

    if not content.strip():
        return SynthesisResult(
            overall_risk_rating="unknown",
            executive_summary="Synthesis could not be generated.",
            remediation_priority=[],
            architectural_recommendations=[],
            usage=usage,
            duration_ms=duration_ms,
        )

    result = _parse_synthesis_response(content)
    result.usage = usage
    result.duration_ms = duration_ms
    return result


def _parse_synthesis_response(raw: str) -> SynthesisResult:
    """Parse LLM synthesis response into SynthesisResult."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse synthesis response: %s", exc)
        return SynthesisResult(
            overall_risk_rating="unknown",
            executive_summary="Failed to parse synthesis.",
            remediation_priority=[],
            architectural_recommendations=[],
            usage=TokenUsage(),
            duration_ms=0,
        )

    if not isinstance(data, dict):
        return SynthesisResult(
            overall_risk_rating="unknown",
            executive_summary="Invalid synthesis format.",
            remediation_priority=[],
            architectural_recommendations=[],
            usage=TokenUsage(),
            duration_ms=0,
        )

    # Parse remediation items
    rem_items: list[RemediationItem] = []
    for item in data.get("remediation_priority", []):
        try:
            rem_items.append(RemediationItem(
                priority=int(item.get("priority", len(rem_items) + 1)),
                finding_refs=item.get("finding_refs", []),
                action=item.get("action", ""),
                effort=item.get("effort", "medium"),
                impact=item.get("impact", "medium"),
            ))
        except (TypeError, ValueError) as exc:
            logger.warning("Skipping malformed remediation item: %s", exc)

    return SynthesisResult(
        overall_risk_rating=data.get("overall_risk_rating", "unknown"),
        executive_summary=data.get("executive_summary", ""),
        remediation_priority=rem_items,
        architectural_recommendations=data.get("architectural_recommendations", []),
        usage=TokenUsage(),
        duration_ms=0,
    )
