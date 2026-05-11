"""NIST-based savings calculator.

Estimates cost savings from catching security findings pre-commit vs. later stages.

Based on:
- NIST SP 800-65 cost-of-defect curves
- IBM Systems Sciences Institute relative cost data
- Industry standard: fixing in production costs 30x more than at development time

Cost multipliers represent how much MORE EXPENSIVE it would be to fix the same
finding at a later stage in the SDLC:
  Pre-commit (here):  1x (baseline — what we do)
  Build/CI:           6.5x
  QA/Testing:         15x
  Production:         30x (critical), 15x (high), 6x (medium), 2x (low)

Savings = production_multiplier × base_cost — we assume the finding WOULD have
reached production without this tool catching it.
"""

from __future__ import annotations

from ..config import settings

# NIST-derived production fix cost multipliers by severity
_SEVERITY_MULTIPLIER = {
    "critical": 30.0,
    "high": 15.0,
    "medium": 6.0,
    "low": 2.0,
}


def calculate_finding_savings(severity: str) -> float:
    """Calculate estimated USD savings for catching a single finding pre-commit.

    Formula: base_cost × (production_multiplier - 1)
    The -1 accounts for the fact that fixing pre-commit still has a cost (1x).
    """
    multiplier = _SEVERITY_MULTIPLIER.get(severity.lower(), 2.0)
    return round(settings.BASE_FINDING_COST_USD * (multiplier - 1), 2)


def calculate_scan_savings(findings: list[dict]) -> float:
    """Calculate total estimated savings for all findings in a scan.

    Args:
        findings: List of dicts with at least a 'severity' key.

    Returns:
        Total estimated savings in USD.
    """
    if not findings:
        return 0.0
    total = sum(calculate_finding_savings(f.get("severity", "low")) for f in findings)
    return round(total, 2)
