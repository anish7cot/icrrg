"""Precision / Recall / F1 computation and finding-matching utilities."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalResult:
    """Aggregate evaluation metrics for one run."""

    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class ScenarioResult:
    """Per-scenario evaluation outcome."""

    scenario_id: str
    description: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    matched: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Finding matching
# ---------------------------------------------------------------------------

@dataclass
class ActualFinding:
    """Normalised representation of an actual finding from any engine."""

    finding_type: str  # e.g. "secret:aws-access-key-id", "llm:Injection"
    severity: str
    file_path: str
    line_number: int


@dataclass
class ExpectedFinding:
    """What we expect the engine to produce for a benchmark scenario."""

    finding_type: str  # prefix match — "secret:" matches "secret:aws-access-key-id"
    severity: str | None = None  # None = don't check severity
    file_path: str | None = None  # None = don't check file
    line_number: int | None = None  # None = don't check line


def _match_one(
    expected: ExpectedFinding,
    actual: ActualFinding,
    line_tolerance: int = 0,
) -> bool:
    """Return True if *actual* satisfies *expected*."""
    # finding_type: prefix match (e.g. "secret:" matches "secret:aws-access-key-id")
    if not actual.finding_type.startswith(expected.finding_type):
        return False
    if expected.severity is not None and actual.severity != expected.severity:
        return False
    if expected.file_path is not None and actual.file_path != expected.file_path:
        return False
    if expected.line_number is not None and actual.line_number is not None:
        if abs(actual.line_number - expected.line_number) > line_tolerance:
            return False
    return True


def match_findings(
    expected: list[ExpectedFinding],
    actual: list[ActualFinding],
    line_tolerance: int = 0,
) -> tuple[int, int, int, list[str], list[str], list[str]]:
    """Match actual findings against expected, return (tp, fp, fn, matched, missed, extra).

    Each expected finding can match at most one actual finding (greedy).
    ``line_tolerance`` allows fuzzy line matching (e.g. ±2 for LLM outputs).
    """
    used_actual: set[int] = set()
    matched_labels: list[str] = []
    missed_labels: list[str] = []

    for exp in expected:
        found = False
        for i, act in enumerate(actual):
            if i in used_actual:
                continue
            if _match_one(exp, act, line_tolerance):
                used_actual.add(i)
                matched_labels.append(exp.finding_type)
                found = True
                break
        if not found:
            missed_labels.append(exp.finding_type)

    extra_labels = [
        actual[i].finding_type for i in range(len(actual)) if i not in used_actual
    ]

    tp = len(matched_labels)
    fn = len(missed_labels)
    fp = len(extra_labels)
    return tp, fp, fn, matched_labels, missed_labels, extra_labels


def compute_precision(tp: int, fp: int) -> float:
    denom = tp + fp
    return tp / denom if denom else 0.0


def compute_recall(tp: int, fn: int) -> float:
    denom = tp + fn
    return tp / denom if denom else 0.0


def compute_f1(precision: float, recall: float) -> float:
    denom = precision + recall
    return 2 * precision * recall / denom if denom else 0.0
