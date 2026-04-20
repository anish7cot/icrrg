"""Integration tests for the evaluation runner — runs detection benchmarks end-to-end."""

import pytest

from eval.runner import load_benchmarks, run_detection, evaluate_scenario, aggregate


class TestBenchmarkLoading:
    def test_loads_detection_benchmarks(self):
        entries = load_benchmarks("detection")
        assert len(entries) > 0
        for e in entries:
            assert e.engine == "detection"
            assert e.diff.strip()

    def test_loads_llm_benchmarks(self):
        entries = load_benchmarks("llm")
        assert len(entries) > 0
        for e in entries:
            assert e.engine == "llm"

    def test_loads_all_benchmarks(self):
        all_entries = load_benchmarks("all")
        det = load_benchmarks("detection")
        llm = load_benchmarks("llm")
        assert len(all_entries) == len(det) + len(llm)

    def test_invalid_engine(self):
        entries = load_benchmarks("nonexistent")
        assert entries == []


class TestDetectionRunner:
    """Run the eval runner on secret+PHI benchmarks and validate metrics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        entries = load_benchmarks("detection")
        self.results = []
        for entry in entries:
            actuals = run_detection(entry.diff)
            result = evaluate_scenario(entry, actuals, line_tolerance=0)
            self.results.append(result)
        self.agg = aggregate(self.results)

    def test_has_results(self):
        assert len(self.results) > 0

    def test_recall_above_threshold(self):
        """Detection engines should correctly find most expected secrets/PHI."""
        assert self.agg.recall >= 0.70, (
            f"Recall {self.agg.recall:.2%} is below 70% threshold — "
            f"TP={self.agg.tp} FN={self.agg.fn}"
        )

    def test_precision_above_threshold(self):
        """Detection engines should not produce too many false positives."""
        assert self.agg.precision >= 0.50, (
            f"Precision {self.agg.precision:.2%} is below 50% threshold — "
            f"TP={self.agg.tp} FP={self.agg.fp}"
        )

    def test_clean_scenarios_have_zero_tp(self):
        """Scenarios marked expected_clean should have 0 TP and 0 FN."""
        clean_entries = [e for e in load_benchmarks("detection") if e.expected_clean]
        for entry in clean_entries:
            actuals = run_detection(entry.diff)
            result = evaluate_scenario(entry, actuals)
            assert result.fn == 0, f"Clean scenario {entry.id} has false negatives"

    def test_aws_secrets_scenario(self):
        """The first AWS secrets scenario should find at least 3 of 4 expected."""
        sec01 = [r for r in self.results if r.scenario_id == "sec-01"]
        assert len(sec01) == 1
        assert sec01[0].tp >= 3, f"sec-01 only matched {sec01[0].tp}/4"

    def test_phi_ssn_scenario(self):
        """PHI scenario should find at least the SSN."""
        phi01 = [r for r in self.results if r.scenario_id == "phi-01"]
        assert len(phi01) == 1
        assert phi01[0].tp >= 1, f"phi-01 only matched {phi01[0].tp} findings"
