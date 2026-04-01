"""Render role-specific LLM prompts from aggregated scan data."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.reports.aggregator import AggregationResult

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape([]),
    trim_blocks=True,
    lstrip_blocks=True,
)

VALID_AUDIENCES = {"developer", "manager", "leadership"}


def build_report_prompt(
    aggregation: AggregationResult,
    audience_type: str,
) -> str:
    """Render a Jinja2 template for the given audience using aggregated data.

    Returns the fully rendered prompt string ready to send to an LLM.
    """
    if audience_type not in VALID_AUDIENCES:
        raise ValueError(
            f"Unknown audience_type '{audience_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_AUDIENCES))}"
        )

    template = _env.get_template(f"{audience_type}.j2")
    return template.render(**aggregation.model_dump())
