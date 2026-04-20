"""Unit tests for eval.metrics — precision, recall, F1, and finding matching."""

import pytest

from eval.metrics import (
    ActualFinding,
    EvalResult,
    ExpectedFinding,
    ScenarioResult,
    compute_f1,
    compute_precision,
    compute_recall,
    match_findings,
)


# ---------------------------------------------------------------------------
# compute_precision / compute_recall / compute_f1
# ---------------------------------------------------------------------------

class TestComputeFunctions:
    def test_precision_basic(self):
        assert compute_precision(8, 2) == pytest.approx(0.8)

    def test_precision_perfect(self):
        assert compute_precision(10, 0) == pytest.approx(1.0)

    def test_precision_zero_denom(self):
        assert compute_precision(0, 0) == 0.0

    def test_recall_basic(self):
        assert compute_recall(8, 2) == pytest.approx(0.8)

    def test_recall_perfect(self):
        assert compute_recall(10, 0) == pytest.approx(1.0)

    def test_recall_zero_denom(self):
        assert compute_recall(0, 0) == 0.0

    def test_f1_basic(self):
        p, r = 0.8, 0.6
        expected = 2 * 0.8 * 0.6 / (0.8 + 0.6)
        assert compute_f1(p, r) == pytest.approx(expected)

    def test_f1_perfect(self):
        assert compute_f1(1.0, 1.0) == pytest.approx(1.0)

    def test_f1_zero(self):
        assert compute_f1(0.0, 0.0) == 0.0

    def test_f1_one_zero(self):
        assert compute_f1(1.0, 0.0) == 0.0
        assert compute_f1(0.0, 1.0) == 0.0


# ---------------------------------------------------------------------------
# EvalResult dataclass
# ---------------------------------------------------------------------------

class TestEvalResult:
    def test_properties(self):
        r = EvalResult(tp=8, fp=2, fn=1)
        assert r.precision == pytest.approx(0.8)
        assert r.recall == pytest.approx(8 / 9)
        expected_f1 = 2 * 0.8 * (8 / 9) / (0.8 + 8 / 9)
        assert r.f1 == pytest.approx(expected_f1)

    def test_empty(self):
        r = EvalResult()
        assert r.precision == 0.0
        assert r.recall == 0.0
        assert r.f1 == 0.0

    def test_all_fp(self):
        r = EvalResult(tp=0, fp=5, fn=0)
        assert r.precision == 0.0
        assert r.recall == 0.0  # 0/(0+0)

    def test_all_fn(self):
        r = EvalResult(tp=0, fp=0, fn=5)
        assert r.precision == 0.0
        assert r.recall == 0.0


# ---------------------------------------------------------------------------
# match_findings
# ---------------------------------------------------------------------------

class TestMatchFindings:
    def test_perfect_match(self):
        expected = [
            ExpectedFinding(finding_type="secret:aws-access-key-id", severity="critical", file_path="config.py", line_number=4),
        ]
        actual = [
            ActualFinding(finding_type="secret:aws-access-key-id", severity="critical", file_path="config.py", line_number=4),
        ]
        tp, fp, fn, matched, missed, extra = match_findings(expected, actual)
        assert tp == 1
        assert fp == 0
        assert fn == 0
        assert matched == ["secret:aws-access-key-id"]
        assert missed == []
        assert extra == []

    def test_prefix_match(self):
        """Expected 'secret:' should match actual 'secret:password-assignment'"""
        expected = [ExpectedFinding(finding_type="secret:")]
        actual = [ActualFinding(finding_type="secret:password-assignment", severity="high", file_path="f.py", line_number=1)]
        tp, fp, fn, _, _, _ = match_findings(expected, actual)
        assert tp == 1
        assert fp == 0

    def test_false_positive(self):
        expected = []
        actual = [
            ActualFinding(finding_type="secret:generic-api-key", severity="high", file_path="f.py", line_number=1),
        ]
        tp, fp, fn, _, _, extra = match_findings(expected, actual)
        assert tp == 0
        assert fp == 1
        assert extra == ["secret:generic-api-key"]

    def test_false_negative(self):
        expected = [
            ExpectedFinding(finding_type="secret:aws-access-key-id", severity="critical"),
        ]
        actual = []
        tp, fp, fn, _, missed, _ = match_findings(expected, actual)
        assert tp == 0
        assert fn == 1
        assert missed == ["secret:aws-access-key-id"]

    def test_line_tolerance(self):
        expected = [ExpectedFinding(finding_type="llm:", line_number=10)]
        actual = [ActualFinding(finding_type="llm:Injection", severity="critical", file_path="f.py", line_number=12)]

        # Without tolerance — no match
        tp, fp, fn, _, _, _ = match_findings(expected, actual, line_tolerance=0)
        assert tp == 0 and fn == 1 and fp == 1

        # With ±2 tolerance — match
        tp, fp, fn, _, _, _ = match_findings(expected, actual, line_tolerance=2)
        assert tp == 1 and fn == 0 and fp == 0

    def test_line_tolerance_exceeded(self):
        expected = [ExpectedFinding(finding_type="llm:", line_number=10)]
        actual = [ActualFinding(finding_type="llm:Injection", severity="critical", file_path="f.py", line_number=13)]
        tp, fp, fn, _, _, _ = match_findings(expected, actual, line_tolerance=2)
        assert tp == 0 and fn == 1 and fp == 1

    def test_multiple_findings(self):
        expected = [
            ExpectedFinding(finding_type="secret:aws-access-key-id"),
            ExpectedFinding(finding_type="secret:password-assignment"),
        ]
        actual = [
            ActualFinding(finding_type="secret:aws-access-key-id", severity="critical", file_path="f.py", line_number=1),
            ActualFinding(finding_type="secret:password-assignment", severity="high", file_path="f.py", line_number=5),
            ActualFinding(finding_type="entropy:high-entropy-string", severity="medium", file_path="f.py", line_number=1),
        ]
        tp, fp, fn, matched, missed, extra = match_findings(expected, actual)
        assert tp == 2
        assert fp == 1
        assert fn == 0
        assert "entropy:high-entropy-string" in extra

    def test_severity_mismatch(self):
        expected = [ExpectedFinding(finding_type="secret:aws-access-key-id", severity="critical")]
        actual = [ActualFinding(finding_type="secret:aws-access-key-id", severity="high", file_path="f.py", line_number=1)]
        tp, fp, fn, _, _, _ = match_findings(expected, actual)
        assert tp == 0  # severity mismatch
        assert fn == 1
        assert fp == 1

    def test_file_path_mismatch(self):
        expected = [ExpectedFinding(finding_type="secret:", file_path="a.py")]
        actual = [ActualFinding(finding_type="secret:aws-access-key-id", severity="critical", file_path="b.py", line_number=1)]
        tp, fp, fn, _, _, _ = match_findings(expected, actual)
        assert tp == 0
        assert fn == 1

    def test_none_fields_skip_check(self):
        """When expected severity/file/line are None, they're not checked."""
        expected = [ExpectedFinding(finding_type="secret:")]
        actual = [ActualFinding(finding_type="secret:something", severity="low", file_path="any.py", line_number=99)]
        tp, fp, fn, _, _, _ = match_findings(expected, actual)
        assert tp == 1

    def test_empty_both(self):
        tp, fp, fn, _, _, _ = match_findings([], [])
        assert tp == 0 and fp == 0 and fn == 0
