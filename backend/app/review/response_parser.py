"""Validate and normalise raw LLM review output into Pydantic models."""

from __future__ import annotations

import json
import logging
from enum import Enum

from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity enum (canonical)
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_SEVERITY_ALIASES: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "crit": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "med": Severity.MEDIUM,
    "moderate": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.LOW,
    "informational": Severity.LOW,
}


# ---------------------------------------------------------------------------
# Pydantic model for a single LLM finding
# ---------------------------------------------------------------------------

class ReviewFindingModel(BaseModel):
    """Validated representation of a single LLM review finding."""

    severity: Severity
    category: str
    file: str
    line: int
    issue: str
    explanation: str
    suggestion: str
    approximate_line: bool = False  # set True if line couldn't be validated

    @field_validator("severity", mode="before")
    @classmethod
    def normalise_severity(cls, v: str) -> Severity:
        if isinstance(v, Severity):
            return v
        mapped = _SEVERITY_ALIASES.get(str(v).strip().lower())
        if mapped is None:
            raise ValueError(f"Unknown severity: {v!r}")
        return mapped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_llm_response(raw: str) -> list[ReviewFindingModel]:
    """Parse raw LLM text into validated finding models.

    Handles markdown-fenced JSON and tolerates minor issues.
    Returns an empty list if the response is fundamentally broken.
    """
    text = raw.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(text)

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of findings")

    findings: list[ReviewFindingModel] = []
    for idx, item in enumerate(data):
        try:
            findings.append(ReviewFindingModel.model_validate(item))
        except Exception as exc:
            logger.warning("Skipping malformed finding #%d: %s", idx, exc)

    return findings


def validate_line_numbers(
    findings: list[ReviewFindingModel],
    valid_lines: dict[str, set[int]],
) -> list[ReviewFindingModel]:
    """Mark findings whose line numbers don't appear in the diff as approximate.

    Args:
        findings: Parsed findings from the LLM.
        valid_lines: Mapping of file path → set of added line numbers from the diff.
    """
    for f in findings:
        file_lines = valid_lines.get(f.file, set())
        if file_lines and f.line not in file_lines:
            f.approximate_line = True
    return findings
