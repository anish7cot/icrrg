"""Pydantic schema for benchmark JSONL entries."""

from __future__ import annotations

from pydantic import BaseModel


class ExpectedFinding(BaseModel):
    """One expected finding in a benchmark scenario."""

    finding_type: str  # prefix like "secret:aws-access-key-id" or "phi:ssn"
    severity: str | None = None
    file_path: str | None = None
    line_number: int | None = None


class BenchmarkEntry(BaseModel):
    """A single labeled benchmark scenario."""

    id: str
    description: str
    engine: str  # "detection" or "llm"
    diff: str
    expected_findings: list[ExpectedFinding] = []
    expected_clean: bool = False
