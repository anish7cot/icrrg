"""Developer scoreboard calculation engine.

Scientific methodology based on:
- CWE Density metric (MITRE) — clean scan rate
- OWASP SAMM "Defect Tracking" maturity — responsiveness/engagement
- Statistical Process Control (SPC) — improvement trends

Composite score = security(40%) + responsiveness(30%) + improvement(30%)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoreBreakdown:
    """Detailed scoring breakdown for a developer."""
    security_score: float       # 0-100 (higher = better code hygiene)
    responsiveness_score: float  # 0-100 (how actively they engage with findings)
    improvement_score: float    # 0-100 (trend vs prior period)
    composite_score: float      # 0-100 weighted final

    # Input metrics
    total_scans: int
    total_findings: int
    clean_scan_count: int
    clean_scan_rate: float
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    findings_per_scan: float
    weighted_finding_density: float
    feedback_given_count: int
    feedback_rate: float
    improvement_rate: float


# Weights for composite score
_SECURITY_WEIGHT = 0.40
_RESPONSIVENESS_WEIGHT = 0.30
_IMPROVEMENT_WEIGHT = 0.30

# Severity penalties for security score (per-scan average)
_SEVERITY_PENALTY = {
    "critical": 5.0,
    "high": 3.0,
    "medium": 1.0,
    "low": 0.0,
}

# Severity weights for density calculation
_SEVERITY_DENSITY_WEIGHT = {
    "critical": 10.0,
    "high": 7.0,
    "medium": 4.0,
    "low": 1.0,
}


def calculate_security_score(
    total_scans: int,
    clean_scan_count: int,
    critical_findings: int,
    high_findings: int,
    medium_findings: int,
) -> float:
    """Calculate security score (0-100) based on clean scan rate and severity.

    Scientific basis: CWE Density metric — measures defect density per unit of work.
    Clean scan rate is the inverse of defect density.
    """
    if total_scans == 0:
        return 50.0  # Neutral — no data

    clean_rate = clean_scan_count / total_scans
    base = clean_rate * 100.0

    # Apply per-scan-average severity penalties
    avg_critical = critical_findings / total_scans
    avg_high = high_findings / total_scans
    avg_medium = medium_findings / total_scans

    penalty = (
        avg_critical * _SEVERITY_PENALTY["critical"]
        + avg_high * _SEVERITY_PENALTY["high"]
        + avg_medium * _SEVERITY_PENALTY["medium"]
    )

    score = base - penalty
    return max(0.0, min(100.0, round(score, 2)))


def calculate_responsiveness_score(
    total_findings_in_user_scans: int,
    feedback_given_count: int,
) -> float:
    """Calculate responsiveness score (0-100) based on engagement with findings.

    Scientific basis: OWASP SAMM "Defect Tracking" — higher maturity requires
    active triage and feedback on all findings.
    """
    if total_findings_in_user_scans == 0:
        return 50.0  # Neutral — nothing to respond to

    feedback_rate = feedback_given_count / total_findings_in_user_scans
    base = min(1.0, feedback_rate) * 100.0

    # Bonus for high engagement
    if feedback_rate > 0.8:
        base = min(100.0, base + 10.0)

    return round(base, 2)


def calculate_improvement_score(
    current_density: float,
    previous_density: float | None,
) -> float:
    """Calculate improvement score (0-100) comparing current vs prior period.

    Scientific basis: Statistical Process Control (SPC) — trend analysis comparing
    current performance against historical baseline.

    50 = no change (neutral baseline)
    100 = eliminated all findings
    0 = findings doubled
    """
    if previous_density is None or previous_density == 0:
        return 50.0  # No prior data — neutral

    if current_density == 0 and previous_density > 0:
        return 100.0  # Perfect improvement

    change_ratio = (previous_density - current_density) / previous_density
    # Map: -1.0 (doubled) → 0, 0 (unchanged) → 50, 1.0 (eliminated) → 100
    score = 50.0 + (change_ratio * 50.0)
    return max(0.0, min(100.0, round(score, 2)))


def calculate_weighted_density(
    critical: int, high: int, medium: int, low: int, total_scans: int
) -> float:
    """Calculate severity-weighted finding density per scan."""
    if total_scans == 0:
        return 0.0
    weighted = (
        critical * _SEVERITY_DENSITY_WEIGHT["critical"]
        + high * _SEVERITY_DENSITY_WEIGHT["high"]
        + medium * _SEVERITY_DENSITY_WEIGHT["medium"]
        + low * _SEVERITY_DENSITY_WEIGHT["low"]
    )
    return round(weighted / total_scans, 4)


def calculate_composite_score(
    security: float, responsiveness: float, improvement: float
) -> float:
    """Calculate weighted composite score."""
    composite = (
        security * _SECURITY_WEIGHT
        + responsiveness * _RESPONSIVENESS_WEIGHT
        + improvement * _IMPROVEMENT_WEIGHT
    )
    return round(composite, 2)


def compute_full_score(
    total_scans: int,
    total_findings: int,
    clean_scan_count: int,
    critical_findings: int,
    high_findings: int,
    medium_findings: int,
    low_findings: int,
    feedback_given_count: int,
    total_findings_in_scans: int,
    previous_density: float | None,
) -> ScoreBreakdown:
    """Compute the full score breakdown for a developer period."""
    clean_scan_rate = clean_scan_count / total_scans if total_scans > 0 else 0.0
    findings_per_scan = total_findings / total_scans if total_scans > 0 else 0.0
    weighted_density = calculate_weighted_density(
        critical_findings, high_findings, medium_findings, low_findings, total_scans
    )
    feedback_rate = feedback_given_count / total_findings_in_scans if total_findings_in_scans > 0 else 0.0

    security = calculate_security_score(
        total_scans, clean_scan_count, critical_findings, high_findings, medium_findings
    )
    responsiveness = calculate_responsiveness_score(total_findings_in_scans, feedback_given_count)
    improvement = calculate_improvement_score(weighted_density, previous_density)
    composite = calculate_composite_score(security, responsiveness, improvement)

    improvement_rate = 0.0
    if previous_density is not None and previous_density > 0:
        improvement_rate = round((previous_density - weighted_density) / previous_density * 100, 2)

    return ScoreBreakdown(
        security_score=security,
        responsiveness_score=responsiveness,
        improvement_score=improvement,
        composite_score=composite,
        total_scans=total_scans,
        total_findings=total_findings,
        clean_scan_count=clean_scan_count,
        clean_scan_rate=round(clean_scan_rate, 4),
        critical_findings=critical_findings,
        high_findings=high_findings,
        medium_findings=medium_findings,
        low_findings=low_findings,
        findings_per_scan=round(findings_per_scan, 2),
        weighted_finding_density=weighted_density,
        feedback_given_count=feedback_given_count,
        feedback_rate=round(feedback_rate, 4),
        improvement_rate=improvement_rate,
    )
