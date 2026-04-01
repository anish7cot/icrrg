"""Abstract base for LLM review providers."""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class ReviewFinding:
    """Single finding returned by an LLM code review."""

    severity: str  # critical | high | medium | low
    category: str
    file: str
    line: int
    issue: str
    explanation: str
    suggestion: str


class BaseLLMProvider(abc.ABC):
    """Interface every LLM provider must implement."""

    @abc.abstractmethod
    async def review(self, diff_text: str) -> list[ReviewFinding]:
        """Analyse a unified diff and return security findings."""


def get_provider() -> BaseLLMProvider:
    """Factory — return the provider configured by ``LLM_PROVIDER`` env var."""
    from ..config import settings

    name = getattr(settings, "LLM_PROVIDER", "openai")

    if name == "mock":
        from .mock_provider import MockProvider
        return MockProvider()

    # Default: OpenAI-compatible (works with OpenRouter)
    from .openai_provider import OpenAIProvider
    return OpenAIProvider()
