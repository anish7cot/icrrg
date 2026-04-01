"""Tests for LLM providers."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.base import BaseLLMProvider, ReviewFinding, get_provider
from app.llm.mock_provider import MockProvider
from app.llm.openai_provider import OpenAIProvider, _parse_findings


# ---------------------------------------------------------------------------
# _parse_findings unit tests
# ---------------------------------------------------------------------------

class TestParseFindingsUnit:
    def test_valid_json_array(self):
        raw = json.dumps([{
            "severity": "critical", "category": "Injection", "file": "a.py",
            "line": 10, "issue": "SQLi", "explanation": "Bad", "suggestion": "Fix"
        }])
        result = _parse_findings(raw)
        assert len(result) == 1
        assert result[0].severity == "critical"
        assert result[0].line == 10

    def test_empty_array(self):
        assert _parse_findings("[]") == []

    def test_strips_markdown_fences(self):
        raw = "```json\n[]\n```"
        assert _parse_findings(raw) == []

    def test_skips_findings_with_missing_keys(self):
        raw = json.dumps([
            {"severity": "high", "category": "X"},  # missing keys
            {"severity": "low", "category": "Y", "file": "b.py", "line": 1,
             "issue": "ok", "explanation": "ok", "suggestion": "ok"},
        ])
        result = _parse_findings(raw)
        assert len(result) == 1
        assert result[0].severity == "low"

    def test_raises_on_non_array(self):
        with pytest.raises(ValueError, match="JSON array"):
            _parse_findings('{"key": "val"}')

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_findings("not json at all")


# ---------------------------------------------------------------------------
# MockProvider tests
# ---------------------------------------------------------------------------

class TestMockProvider:
    @pytest.fixture
    def provider(self):
        return MockProvider()

    def test_detects_sql_injection(self, provider):
        diff = '+    query = "SELECT * FROM users WHERE id = \'" + user_id + "\'"'
        findings = asyncio.get_event_loop().run_until_complete(provider.review(diff))
        assert len(findings) >= 1
        assert any(f.category == "Injection" for f in findings)

    def test_detects_hardcoded_secret(self, provider):
        diff = "+API_KEY = 'sk-live-abc123'"
        findings = asyncio.get_event_loop().run_until_complete(provider.review(diff))
        assert len(findings) >= 1
        assert any(f.category == "Hardcoded Secret" for f in findings)

    def test_detects_command_injection(self, provider):
        diff = "+    subprocess.run('curl ' + url, shell=True)"
        findings = asyncio.get_event_loop().run_until_complete(provider.review(diff))
        assert len(findings) >= 1
        assert any(f.category == "Injection" for f in findings)

    def test_detects_insecure_http(self, provider):
        diff = '+    requests.post("http://api.example.com", verify=False)'
        findings = asyncio.get_event_loop().run_until_complete(provider.review(diff))
        assert len(findings) >= 1
        assert any(f.category == "Insecure Transport" for f in findings)

    def test_clean_diff_returns_empty(self, provider):
        diff = "+def add(a, b):\n+    return a + b"
        findings = asyncio.get_event_loop().run_until_complete(provider.review(diff))
        assert findings == []

    def test_multiple_issues(self, provider):
        diff = "+API_KEY = 'secret'\n+subprocess.run('ls ' + x, shell=True)"
        findings = asyncio.get_event_loop().run_until_complete(provider.review(diff))
        assert len(findings) >= 2


# ---------------------------------------------------------------------------
# OpenAIProvider tests (mocked API)
# ---------------------------------------------------------------------------

class TestOpenAIProvider:
    def _make_mock_response(self, content: str):
        choice = MagicMock()
        choice.message.content = content
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @patch("app.llm.openai_provider.openai.AsyncOpenAI")
    def test_review_returns_findings(self, mock_cls):
        findings_json = json.dumps([{
            "severity": "high", "category": "Injection", "file": "a.py",
            "line": 5, "issue": "SQLi", "explanation": "Bad", "suggestion": "Fix"
        }])
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=self._make_mock_response(findings_json)
        )
        mock_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = asyncio.get_event_loop().run_until_complete(
            provider.review("some diff")
        )
        assert len(result) == 1
        assert result[0].severity == "high"

    @patch("app.llm.openai_provider.openai.AsyncOpenAI")
    def test_review_empty_on_clean_diff(self, mock_cls):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=self._make_mock_response("[]")
        )
        mock_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = asyncio.get_event_loop().run_until_complete(
            provider.review("clean diff")
        )
        assert result == []

    @patch("app.llm.openai_provider.openai.AsyncOpenAI")
    def test_retry_on_rate_limit(self, mock_cls):
        import openai as oai
        findings_json = json.dumps([{
            "severity": "low", "category": "X", "file": "b.py",
            "line": 1, "issue": "ok", "explanation": "ok", "suggestion": "ok"
        }])
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                oai.RateLimitError(
                    message="rate limited",
                    response=MagicMock(status_code=429),
                    body=None,
                ),
                self._make_mock_response(findings_json),
            ]
        )
        mock_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = asyncio.get_event_loop().run_until_complete(
            provider.review("diff")
        )
        assert len(result) == 1
        assert mock_client.chat.completions.create.await_count == 2

    @patch("app.llm.openai_provider.openai.AsyncOpenAI")
    def test_graceful_failure_on_persistent_error(self, mock_cls):
        import openai as oai
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=oai.RateLimitError(
                message="rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
        )
        mock_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = asyncio.get_event_loop().run_until_complete(
            provider.review("diff")
        )
        # Should return empty, not raise
        assert result == []

    @patch("app.llm.openai_provider.openai.AsyncOpenAI")
    def test_graceful_failure_on_bad_json(self, mock_cls):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=self._make_mock_response("not valid json!!")
        )
        mock_cls.return_value = mock_client

        provider = OpenAIProvider()
        result = asyncio.get_event_loop().run_until_complete(
            provider.review("diff")
        )
        assert result == []


# ---------------------------------------------------------------------------
# get_provider factory tests
# ---------------------------------------------------------------------------

class TestGetProvider:
    def test_returns_mock_provider(self):
        with patch.dict("os.environ", {"LLM_PROVIDER": "mock"}):
            from importlib import reload
            import app.config
            reload(app.config)
            import app.llm.base as base_mod
            reload(base_mod)
            provider = base_mod.get_provider()
            assert isinstance(provider, MockProvider)
            # Restore
            reload(app.config)

    def test_returns_openai_provider(self):
        with patch.dict("os.environ", {"LLM_PROVIDER": "openai"}):
            from importlib import reload
            import app.config
            reload(app.config)
            import app.llm.base as base_mod
            reload(base_mod)
            provider = base_mod.get_provider()
            assert isinstance(provider, OpenAIProvider)
            reload(app.config)
