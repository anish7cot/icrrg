"""Finding deduplication — removes duplicates between rule-based and LLM findings."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def deduplicate_findings(findings: list[dict]) -> list[dict]:
    """Remove duplicate findings detected by multiple engines.

    Match criteria:
    - Same file_path
    - Line number within ±2 range
    - Similar finding category (rule-based secret vs LLM Hardcoded Secret, etc.)

    When duplicates found, keep the one with higher confidence.
    """
    if len(findings) <= 1:
        return findings

    # Group by file_path for efficient comparison
    by_file: dict[str, list[dict]] = {}
    for f in findings:
        path = f.get("file_path") or ""
        by_file.setdefault(path, []).append(f)

    deduped: list[dict] = []

    for path, file_findings in by_file.items():
        if len(file_findings) <= 1:
            deduped.extend(file_findings)
            continue

        # Sort by confidence descending so higher-confidence kept first
        file_findings.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
        kept: list[dict] = []

        for f in file_findings:
            is_dup = False
            f_line = f.get("line_number") or 0
            f_type = f.get("finding_type", "")

            for existing in kept:
                e_line = existing.get("line_number") or 0
                e_type = existing.get("finding_type", "")

                # Check line proximity
                if abs(f_line - e_line) > 2:
                    continue

                # Check category similarity
                if _types_overlap(f_type, e_type):
                    is_dup = True
                    break

            if not is_dup:
                kept.append(f)

        deduped.extend(kept)

    return deduped


# Category overlap mappings
_CATEGORY_GROUPS = {
    "secret": {"secret", "hardcoded secret", "credential"},
    "injection": {"injection", "sql injection", "command injection", "xss"},
    "transport": {"insecure transport", "http", "tls"},
    "phi": {"phi", "pii", "sensitive data exposure"},
    "entropy": {"entropy", "random"},
}


def _types_overlap(type_a: str, type_b: str) -> bool:
    """Check if two finding types refer to the same general category."""
    a_lower = type_a.lower()
    b_lower = type_b.lower()

    # Exact prefix match (e.g. secret:aws-key vs llm:Hardcoded Secret)
    a_prefix = a_lower.split(":")[0]
    b_prefix = b_lower.split(":")[0]

    # Same prefix means same engine — not duplicates between engines
    if a_prefix == b_prefix:
        return False

    # Cross-engine: check category groups
    a_cat = a_lower.split(":", 1)[1] if ":" in a_lower else a_lower
    b_cat = b_lower.split(":", 1)[1] if ":" in b_lower else b_lower

    for group_keywords in _CATEGORY_GROUPS.values():
        a_match = any(kw in a_cat for kw in group_keywords)
        b_match = any(kw in b_cat for kw in group_keywords)
        if a_match and b_match:
            return True

    return False
