"""OpenAI-compatible LLM provider (works with OpenRouter)."""

from __future__ import annotations

import json
import logging

import openai

from ..config import settings
from ..review.prompts.system import build_review_prompt
from .base import BaseLLMProvider, ReviewFinding

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_TIMEOUT_SECONDS = 120

# Keys every finding dict must contain.
_REQUIRED_KEYS = {"severity", "category", "file", "line", "issue", "explanation", "suggestion"}


def _parse_findings(raw: str) -> list[ReviewFinding]:
    """Parse the raw LLM response into validated ReviewFinding objects."""
    text = raw.strip()
    # Strip markdown code fences if the model wraps them.
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of findings")

    findings: list[ReviewFinding] = []
    for item in data:
        missing = _REQUIRED_KEYS - set(item.keys())
        if missing:
            logger.warning("Skipping finding with missing keys: %s", missing)
            continue
        findings.append(
            ReviewFinding(
                severity=item["severity"],
                category=item["category"],
                file=item["file"],
                line=int(item["line"]),
                issue=item["issue"],
                explanation=item["explanation"],
                suggestion=item["suggestion"],
            )
        )
    return findings


class OpenAIProvider(BaseLLMProvider):
    """Calls any OpenAI-compatible API (OpenAI, OpenRouter, etc.)."""

    def __init__(self) -> None:
        self._client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=_TIMEOUT_SECONDS,
        )
        self._model = settings.REVIEW_MODEL

    async def review(self, diff_text: str) -> list[ReviewFinding]:
        """Send the diff through the review prompt and return findings."""
        messages = build_review_prompt(diff_text)
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0,
                )
                content = response.choices[0].message.content or "[]"
                return _parse_findings(content)

            except (openai.RateLimitError, openai.APITimeoutError) as exc:
                last_error = exc
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s — retrying",
                        attempt + 1,
                        _MAX_RETRIES + 1,
                        exc,
                    )
                    continue
                logger.error("LLM call failed after %d attempts: %s", _MAX_RETRIES + 1, exc)

            except openai.APIError as exc:
                last_error = exc
                logger.error("LLM API error: %s", exc)
                break

            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                logger.error("Failed to parse LLM response: %s", exc)
                break

        # Graceful failure — return empty findings rather than crashing.
        logger.error("Returning empty findings due to error: %s", last_error)
        return []
