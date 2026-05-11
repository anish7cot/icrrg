"""LLM model pricing lookup table for cost calculation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelPricing:
    """Per-token pricing for a model (USD per 1M tokens)."""
    input_per_million: float
    output_per_million: float


# Pricing table — add models as needed.
# Source: OpenRouter / OpenAI pricing pages.
MODEL_PRICING: dict[str, ModelPricing] = {
    # Free models (OpenRouter)
    "nvidia/nemotron-3-super-120b-a12b:free": ModelPricing(0.0, 0.0),
    # OpenAI
    "gpt-4o": ModelPricing(2.50, 10.00),
    "gpt-4o-mini": ModelPricing(0.15, 0.60),
    "gpt-4-turbo": ModelPricing(10.00, 30.00),
    "gpt-4": ModelPricing(30.00, 60.00),
    "gpt-3.5-turbo": ModelPricing(0.50, 1.50),
    # Anthropic
    "anthropic/claude-3.5-sonnet": ModelPricing(3.00, 15.00),
    "anthropic/claude-3-haiku": ModelPricing(0.25, 1.25),
    # Meta
    "meta-llama/llama-3.1-70b-instruct": ModelPricing(0.52, 0.75),
    "meta-llama/llama-3.1-8b-instruct": ModelPricing(0.06, 0.06),
}

# Default pricing when model not found in table
_DEFAULT_PRICING = ModelPricing(1.00, 2.00)


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given model and token counts."""
    pricing = MODEL_PRICING.get(model, _DEFAULT_PRICING)
    cost = (
        (input_tokens / 1_000_000) * pricing.input_per_million
        + (output_tokens / 1_000_000) * pricing.output_per_million
    )
    return round(cost, 6)
