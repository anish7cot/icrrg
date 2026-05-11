"""Abstract base for LLM review providers."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


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
    reasoning: str = ""  # Chain-of-thought reasoning (Level 2+)


@dataclass
class TokenUsage:
    """Token usage from a single LLM call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Complete response from an LLM call including findings and metadata."""
    findings: list[ReviewFinding] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    duration_ms: int = 0


class BaseLLMProvider(abc.ABC):
    """Interface every LLM provider must implement."""

    @abc.abstractmethod
    async def review(self, diff_text: str) -> list[ReviewFinding]:
        """Analyse a unified diff and return security findings."""

    @abc.abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0) -> LLMResponse:
        """Generic chat completion — returns full response with token usage."""


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
