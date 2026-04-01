"""Tests for the code-review pipeline (response_parser + service)."""

import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock

from app.review.response_parser import (
    ReviewFindingModel,
    Severity,
    parse_llm_response,
    validate_line_numbers,
)
from app.review.service import (
    CodeReviewFinding,
    run_code_review,
    _chunk_diff,
    _build_valid_lines,
)
from app.git.diff_parser import parse_unified_diff
from app.llm.base import ReviewFinding as LLMReviewFinding


# ===================================================================
# response_parser tests
# ===================================================================

class TestParseLlmResponse:
    def test_valid_json(self):
        raw = json.dumps([{
            "severity": "critical", "category": "Injection",
            "file": "a.py", "line": 10,
            "issue": "SQLi", "explanation": "Bad", "suggestion": "Fix"
        }])
        findings = parse_llm_response(raw)
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL
        assert findings[0].category == "Injection"

    def test_empty_array(self):
        assert parse_llm_response("[]") == []

    def test_strips_markdown_fences(self):
        raw = "```json\n[]\n```"
        assert parse_llm_response(raw) == []

    def test_severity_aliases(self):
        raw = json.dumps([{
            "severity": "med", "category": "X",
            "file": "x.py", "line": 1,
            "issue": "x", "explanation": "x", "suggestion": "x"
        }])
        findings = parse_llm_response(raw)
        assert findings[0].severity == Severity.MEDIUM

    def test_skips_malformed_items(self):
        raw = json.dumps([
            {"severity": "high"},  # incomplete
            {
                "severity": "low", "category": "Y",
                "file": "b.py", "line": 1,
                "issue": "ok", "explanation": "ok", "suggestion": "ok"
            },
        ])
        findings = parse_llm_response(raw)
        assert len(findings) == 1

    def test_raises_on_non_array(self):
        with pytest.raises(ValueError, match="JSON array"):
            parse_llm_response('{"key": "val"}')

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_response("not json")

    def test_unknown_severity_skipped(self):
        raw = json.dumps([{
            "severity": "ultra", "category": "X",
            "file": "x.py", "line": 1,
            "issue": "x", "explanation": "x", "suggestion": "x"
        }])
        findings = parse_llm_response(raw)
        assert len(findings) == 0  # skipped due to bad severity


class TestValidateLineNumbers:
    def test_marks_invalid_lines_as_approximate(self):
        f = ReviewFindingModel(
            severity=Severity.HIGH, category="X",
            file="app.py", line=999,
            issue="x", explanation="x", suggestion="x",
        )
        valid_lines = {"app.py": {10, 11, 12}}
        result = validate_line_numbers([f], valid_lines)
        assert result[0].approximate_line is True

    def test_valid_lines_stay_exact(self):
        f = ReviewFindingModel(
            severity=Severity.HIGH, category="X",
            file="app.py", line=10,
            issue="x", explanation="x", suggestion="x",
        )
        valid_lines = {"app.py": {10, 11, 12}}
        result = validate_line_numbers([f], valid_lines)
        assert result[0].approximate_line is False

    def test_unknown_file_not_marked(self):
        f = ReviewFindingModel(
            severity=Severity.LOW, category="X",
            file="unknown.py", line=5,
            issue="x", explanation="x", suggestion="x",
        )
        result = validate_line_numbers([f], {})
        assert result[0].approximate_line is False  # no lines to contradict


# ===================================================================
# service pipeline tests
# ===================================================================

SAMPLE_DIFF = """\
diff --git a/app/db.py b/app/db.py
--- a/app/db.py
+++ b/app/db.py
@@ -10,6 +10,9 @@
 from flask import request

+def get_user(user_id):
+    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
+    return db.execute(query)
"""

MOCK_LLM_FINDING = LLMReviewFinding(
    severity="critical",
    category="Injection",
    file="app/db.py",
    line=12,
    issue="SQL injection via string concatenation.",
    explanation="User input is concatenated into a SQL query.",
    suggestion="Use parameterised queries.",
)


class TestChunkDiff:
    def test_small_diff_not_chunked(self):
        parsed = parse_unified_diff(SAMPLE_DIFF)
        chunks = _chunk_diff(SAMPLE_DIFF, parsed)
        assert len(chunks) == 1
        assert chunks[0] == SAMPLE_DIFF

    def test_large_diff_chunked_by_file(self):
        # Build a diff with many lines across 2 files
        lines_a = "\n".join(f"+line{i}" for i in range(2000))
        lines_b = "\n".join(f"+line{i}" for i in range(2000))
        big_diff = (
            f"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,0 +1,2000 @@\n{lines_a}\n"
            f"diff --git a/b.py b/b.py\n--- a/b.py\n+++ b/b.py\n@@ -1,0 +1,2000 @@\n{lines_b}\n"
        )
        parsed = parse_unified_diff(big_diff)
        chunks = _chunk_diff(big_diff, parsed)
        assert len(chunks) == 2


class TestBuildValidLines:
    def test_extracts_added_lines(self):
        parsed = parse_unified_diff(SAMPLE_DIFF)
        vl = _build_valid_lines(parsed)
        assert "app/db.py" in vl
        assert 11 in vl["app/db.py"]  # first added line
        assert 12 in vl["app/db.py"]
        assert 13 in vl["app/db.py"]


class TestRunCodeReview:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch("app.review.service.get_provider")
    def test_returns_unified_findings(self, mock_get_provider):
        mock_provider = AsyncMock()
        mock_provider.review.return_value = [MOCK_LLM_FINDING]
        mock_get_provider.return_value = mock_provider

        findings = self._run(run_code_review(SAMPLE_DIFF))
        assert len(findings) == 1
        f = findings[0]
        assert isinstance(f, CodeReviewFinding)
        assert f.severity == "critical"
        assert f.rule_name == "llm:Injection"
        assert f.file_path == "app/db.py"
        assert f.line_number == 12
        assert f.confidence == 0.85
        assert f.approximate_line is False

    @patch("app.review.service.get_provider")
    def test_marks_approximate_line(self, mock_get_provider):
        bad_line = LLMReviewFinding(
            severity="high", category="X", file="app/db.py",
            line=999, issue="x", explanation="x", suggestion="x",
        )
        mock_provider = AsyncMock()
        mock_provider.review.return_value = [bad_line]
        mock_get_provider.return_value = mock_provider

        findings = self._run(run_code_review(SAMPLE_DIFF))
        assert len(findings) == 1
        assert findings[0].approximate_line is True
        assert findings[0].confidence == 0.60

    @patch("app.review.service.get_provider")
    def test_empty_diff_returns_empty(self, mock_get_provider):
        findings = self._run(run_code_review(""))
        assert findings == []
        mock_get_provider.assert_not_called()

    @patch("app.review.service.get_provider")
    def test_llm_returns_no_findings(self, mock_get_provider):
        mock_provider = AsyncMock()
        mock_provider.review.return_value = []
        mock_get_provider.return_value = mock_provider

        findings = self._run(run_code_review(SAMPLE_DIFF))
        assert findings == []

    @patch("app.review.service.get_provider")
    def test_multiple_chunks(self, mock_get_provider):
        # Force chunking with a large diff
        lines_a = "\n".join(f"+line{i}" for i in range(2000))
        lines_b = "\n".join(f"+line{i}" for i in range(2000))
        big_diff = (
            f"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,0 +1,2000 @@\n{lines_a}\n"
            f"diff --git a/b.py b/b.py\n--- a/b.py\n+++ b/b.py\n@@ -1,0 +1,2000 @@\n{lines_b}\n"
        )
        finding_a = LLMReviewFinding(
            severity="high", category="Test", file="a.py",
            line=1, issue="issue A", explanation="x", suggestion="x",
        )
        finding_b = LLMReviewFinding(
            severity="low", category="Test", file="b.py",
            line=1, issue="issue B", explanation="x", suggestion="x",
        )
        mock_provider = AsyncMock()
        mock_provider.review.side_effect = [[finding_a], [finding_b]]
        mock_get_provider.return_value = mock_provider

        findings = self._run(run_code_review(big_diff))
        assert len(findings) == 2
        assert mock_provider.review.await_count == 2

    @patch("app.review.service.get_provider")
    def test_invalid_finding_skipped(self, mock_get_provider):
        bad = LLMReviewFinding(
            severity="garbage", category="X", file="a.py",
            line=1, issue="x", explanation="x", suggestion="x",
        )
        good = MOCK_LLM_FINDING
        mock_provider = AsyncMock()
        mock_provider.review.return_value = [bad, good]
        mock_get_provider.return_value = mock_provider

        findings = self._run(run_code_review(SAMPLE_DIFF))
        assert len(findings) == 1
        assert findings[0].severity == "critical"
