"""Level 3 — Cross-finding correlation engine.

Identifies attack chains and compounding risks by analyzing
relationships between individual findings from Levels 1 and 2.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from ..llm.base import TokenUsage, get_provider
from .prompts.correlation import build_correlation_prompt

logger = logging.getLogger(__name__)


@dataclass
class CorrelatedChain:
    """A group of findings that form an attack chain."""
    chain_id: int
    finding_refs: list[int]
    combined_severity: str
    attack_narrative: str
    compounded_risk: str


@dataclass
class CorrelationResult:
    """Output of Level 3 correlation analysis."""
    chains: list[CorrelatedChain]
    usage: TokenUsage
    duration_ms: int


async def run_correlation_analysis(
    findings: list[dict],
) -> CorrelationResult:
    """Run Level 3 cross-finding correlation.

    Args:
        findings: List of finding dicts (from Level 1 + Level 2) with keys:
                  severity, category, file_path, line_number, message

    Returns:
        CorrelationResult with identified attack chains and token usage.
        Returns empty chains list on failure (graceful degradation).
    """
    # Skip if fewer than 2 findings — no correlations possible
    if len(findings) < 2:
        return CorrelationResult(chains=[], usage=TokenUsage(), duration_ms=0)

    # Prepare findings summary for the LLM
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
    messages = build_correlation_prompt(findings_json)

    provider = get_provider()
    try:
        content, usage, duration_ms = await provider.chat_raw(messages, temperature=0)
    except AttributeError:
        # Provider doesn't support chat_raw — use chat() fallback
        response = await provider.chat(messages, temperature=0)
        content = ""
        usage = response.usage
        duration_ms = response.duration_ms

    if not content.strip():
        return CorrelationResult(chains=[], usage=usage, duration_ms=duration_ms)

    # Parse response
    chains = _parse_correlation_response(content)
    return CorrelationResult(chains=chains, usage=usage, duration_ms=duration_ms)


def _parse_correlation_response(raw: str) -> list[CorrelatedChain]:
    """Parse LLM correlation response into CorrelatedChain objects."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse correlation response: %s", exc)
        return []

    if not isinstance(data, list):
        return []

    chains: list[CorrelatedChain] = []
    for item in data:
        try:
            chains.append(CorrelatedChain(
                chain_id=int(item.get("chain_id", len(chains) + 1)),
                finding_refs=item.get("finding_refs", []),
                combined_severity=item.get("combined_severity", "medium"),
                attack_narrative=item.get("attack_narrative", ""),
                compounded_risk=item.get("compounded_risk", ""),
            ))
        except (TypeError, ValueError) as exc:
            logger.warning("Skipping malformed chain: %s", exc)

    return chains
