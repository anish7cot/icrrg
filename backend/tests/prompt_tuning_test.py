"""Prompt tuning test script — runs test diffs through the LLM review pipeline.

Usage:
    poetry run python -m tests.prompt_tuning_test          # run all diffs once
    poetry run python -m tests.prompt_tuning_test --repeat 3  # 3x consistency
"""

import asyncio
import argparse
import json
import sys
import time

# Ensure project root is importable
sys.path.insert(0, ".")

from app.review.service import run_code_review
from tests.fixtures.test_diffs import (
    SQL_INJECTION_DIFF,
    XSS_DIFF,
    DESER_PATH_TRAVERSAL_DIFF,
    CLEAN_DIFF,
)

SCENARIOS = [
    ("SQL Injection", SQL_INJECTION_DIFF, ["injection", "sql"]),
    ("XSS", XSS_DIFF, ["xss", "cross-site", "script"]),
    ("Deserialization / Path Traversal", DESER_PATH_TRAVERSAL_DIFF, ["deserialization", "pickle", "path traversal", "traversal"]),
    ("Clean Code (expect 0 findings)", CLEAN_DIFF, []),
]


def check_expected(findings, expected_keywords: list[str], scenario_name: str) -> bool:
    """Check whether findings match expected keywords. Return True = pass."""
    if not expected_keywords:
        # Clean diff — we expect 0 findings
        if len(findings) == 0:
            print(f"  ✅ PASS — 0 findings (correct)")
            return True
        else:
            print(f"  ⚠️  FALSE POSITIVES — expected 0 findings, got {len(findings)}:")
            for f in findings:
                print(f"     - [{f.severity}] {f.rule_name}: {f.description}")
            return False

    # Vulnerability diff — check that at least 1 finding references one of the keywords
    all_text = " ".join(
        f"{f.rule_name} {f.description} {f.explanation}".lower() for f in findings
    )
    hits = [kw for kw in expected_keywords if kw in all_text]
    if hits:
        print(f"  ✅ PASS — {len(findings)} finding(s), matched keywords: {hits}")
        return True
    else:
        print(f"  ❌ MISS — {len(findings)} finding(s) but none matched {expected_keywords}")
        for f in findings:
            print(f"     - [{f.severity}] {f.rule_name}: {f.description}")
        return False


async def run_scenario(name: str, diff: str, expected: list[str], run_idx: int = 1):
    print(f"\n{'='*60}")
    print(f"Scenario: {name}  (run #{run_idx})")
    print(f"{'='*60}")
    try:
        t0 = time.time()
        findings = await run_code_review(diff)
        elapsed = time.time() - t0
        print(f"  Time: {elapsed:.1f}s  |  Findings: {len(findings)}")
        for f in findings:
            print(f"  [{f.severity:8s}] {f.rule_name:<30s} | {f.file_path}:{f.line_number}")
            print(f"            {f.description}")
        passed = check_expected(findings, expected, name)
        return passed, findings
    except Exception as e:
        print(f"  ⚠️  ERROR: {e}")
        return False, []


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=1, help="Run each scenario N times")
    args = parser.parse_args()

    total_pass = 0
    total_fail = 0

    for name, diff, expected in SCENARIOS:
        for run_idx in range(1, args.repeat + 1):
            passed, _ = await run_scenario(name, diff, expected, run_idx)
            if passed:
                total_pass += 1
            else:
                total_fail += 1

    print(f"\n{'='*60}")
    print(f"SUMMARY: {total_pass} passed, {total_fail} failed out of {total_pass + total_fail}")
    print(f"{'='*60}")

    if total_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
