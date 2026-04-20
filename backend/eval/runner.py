"""Evaluation runner — loads benchmarks, runs detection/LLM engines, reports metrics.

Usage:
    python -m eval.runner                              # detection only, table output
    python -m eval.runner --engine llm --repeat 3      # LLM with 3x consistency
    python -m eval.runner --engine all --output json   # everything, JSON output
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.benchmarks.schema import BenchmarkEntry, ExpectedFinding as BenchmarkExpected
from eval.metrics import (
    ActualFinding,
    EvalResult,
    ExpectedFinding,
    ScenarioResult,
    match_findings,
)

BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmarks"


# ---------------------------------------------------------------------------
# Benchmark loading
# ---------------------------------------------------------------------------

def load_benchmarks(engine_filter: str) -> list[BenchmarkEntry]:
    """Load benchmark entries from base64-encoded JSONL files, filtered by engine."""
    entries: list[BenchmarkEntry] = []
    files = {
        "detection": ["secrets.jsonl", "phi.jsonl"],
        "llm": ["llm_review.jsonl"],
        "all": ["secrets.jsonl", "phi.jsonl", "llm_review.jsonl"],
    }
    for fname in files.get(engine_filter, []):
        # Prefer .b64 encoded version (avoids GitHub push protection),
        # fall back to plain JSONL for local development.
        b64_path = BENCHMARK_DIR / (fname + ".b64")
        plain_path = BENCHMARK_DIR / fname
        if b64_path.exists():
            raw = base64.b64decode(b64_path.read_text(encoding="ascii")).decode("utf-8")
        elif plain_path.exists():
            raw = plain_path.read_text(encoding="utf-8")
        else:
            continue
        for line in raw.strip().splitlines():
            line = line.strip()
            if line:
                entries.append(BenchmarkEntry.model_validate_json(line))
    return entries


# ---------------------------------------------------------------------------
# Pipeline runners
# ---------------------------------------------------------------------------

def run_detection(diff_text: str) -> list[ActualFinding]:
    """Run the full detection pipeline (regex + entropy + NER) on a diff."""
    from app.git.diff_parser import parse_unified_diff
    from app.detection.regex_engine import scan_diff_for_secrets
    from app.detection.entropy import scan_diff_for_entropy
    from app.detection.ner_pipeline import scan_diff_for_phi

    parsed = parse_unified_diff(diff_text)
    findings: list[ActualFinding] = []

    for f in scan_diff_for_secrets(parsed, skip_tests=False):
        findings.append(ActualFinding(
            finding_type=f"secret:{f.rule_name}",
            severity=f.severity,
            file_path=f.file_path,
            line_number=f.line_number,
        ))
    for f in scan_diff_for_entropy(parsed, skip_tests=False):
        findings.append(ActualFinding(
            finding_type=f"entropy:{f.rule_name}",
            severity=f.severity,
            file_path=f.file_path,
            line_number=f.line_number,
        ))
    for f in scan_diff_for_phi(parsed, skip_tests=False):
        findings.append(ActualFinding(
            finding_type=f"phi:{f.rule_name}",
            severity=f.severity,
            file_path=f.file_path,
            line_number=f.line_number,
        ))
    return findings


async def run_llm_review(diff_text: str) -> list[ActualFinding]:
    """Run the LLM code review pipeline on a diff."""
    from app.review.service import run_code_review

    findings: list[ActualFinding] = []
    for f in await run_code_review(diff_text):
        findings.append(ActualFinding(
            finding_type=f"llm:{f.rule_name.removeprefix('llm:')}",
            severity=f.severity,
            file_path=f.file_path,
            line_number=f.line_number,
        ))
    return findings


# ---------------------------------------------------------------------------
# Evaluate one scenario
# ---------------------------------------------------------------------------

def _to_expected(benchmark_expected: list[BenchmarkExpected]) -> list[ExpectedFinding]:
    return [
        ExpectedFinding(
            finding_type=e.finding_type,
            severity=e.severity,
            file_path=e.file_path,
            line_number=e.line_number,
        )
        for e in benchmark_expected
    ]


def evaluate_scenario(
    entry: BenchmarkEntry,
    actuals: list[ActualFinding],
    line_tolerance: int = 0,
) -> ScenarioResult:
    expected = _to_expected(entry.expected_findings)
    tp, fp, fn, matched, missed, extra = match_findings(expected, actuals, line_tolerance)
    return ScenarioResult(
        scenario_id=entry.id,
        description=entry.description,
        tp=tp, fp=fp, fn=fn,
        matched=matched, missed=missed, extra=extra,
    )


# ---------------------------------------------------------------------------
# Aggregate results
# ---------------------------------------------------------------------------

def aggregate(results: list[ScenarioResult]) -> EvalResult:
    agg = EvalResult()
    for r in results:
        agg.tp += r.tp
        agg.fp += r.fp
        agg.fn += r.fn
    return agg


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _print_table(results: list[ScenarioResult], agg: EvalResult, elapsed: float) -> None:
    print(f"\n{'='*80}")
    print(f"{'ID':<10} {'Description':<45} {'TP':>3} {'FP':>3} {'FN':>3} {'Result'}")
    print(f"{'-'*80}")
    for r in results:
        status = "PASS" if r.fn == 0 and r.fp == 0 else ("PARTIAL" if r.tp > 0 else "FAIL")
        print(f"{r.scenario_id:<10} {r.description[:44]:<45} {r.tp:>3} {r.fp:>3} {r.fn:>3} {status}")
        if r.missed:
            print(f"{'':>10}   missed: {', '.join(r.missed)}")
        if r.extra:
            print(f"{'':>10}   extra:  {', '.join(r.extra)}")
    print(f"{'='*80}")
    print(f"  Precision: {agg.precision:.2%}  |  Recall: {agg.recall:.2%}  |  F1: {agg.f1:.2%}")
    print(f"  TP={agg.tp}  FP={agg.fp}  FN={agg.fn}  |  {len(results)} scenarios  |  {elapsed:.1f}s")
    print(f"{'='*80}")


def _print_json(results: list[ScenarioResult], agg: EvalResult, elapsed: float) -> None:
    output = {
        "precision": round(agg.precision, 4),
        "recall": round(agg.recall, 4),
        "f1": round(agg.f1, 4),
        "tp": agg.tp,
        "fp": agg.fp,
        "fn": agg.fn,
        "scenarios": len(results),
        "elapsed_seconds": round(elapsed, 2),
        "details": [
            {
                "id": r.scenario_id,
                "description": r.description,
                "tp": r.tp, "fp": r.fp, "fn": r.fn,
                "matched": r.matched,
                "missed": r.missed,
                "extra": r.extra,
            }
            for r in results
        ],
    }
    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _run(args: argparse.Namespace) -> tuple[list[ScenarioResult], EvalResult, float]:
    entries = load_benchmarks(args.engine)
    if not entries:
        print(f"No benchmark entries found for engine={args.engine}")
        sys.exit(1)

    all_results: list[ScenarioResult] = []
    t0 = time.time()

    for entry in entries:
        is_llm = entry.engine == "llm"
        line_tol = 2 if is_llm else 0

        for run_idx in range(1, args.repeat + 1 if is_llm else 2):
            if is_llm:
                actuals = await run_llm_review(entry.diff)
            else:
                actuals = run_detection(entry.diff)

            result = evaluate_scenario(entry, actuals, line_tol)
            all_results.append(result)

    elapsed = time.time() - t0
    agg = aggregate(all_results)
    return all_results, agg, elapsed


async def main() -> None:
    parser = argparse.ArgumentParser(description="SecureDiff evaluation runner")
    parser.add_argument(
        "--engine",
        choices=["detection", "llm", "all"],
        default="detection",
        help="Which engine(s) to evaluate (default: detection)",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Run each LLM scenario N times for consistency (default: 1)",
    )
    parser.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    results, agg, elapsed = await _run(args)

    if args.output == "json":
        _print_json(results, agg, elapsed)
    else:
        _print_table(results, agg, elapsed)

    if agg.fn > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
