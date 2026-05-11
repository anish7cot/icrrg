"""add multilevel reasoning and metrics tables

Revision ID: c8a9f2b1d3e4
Revises: 5c4e5a090ea6
Create Date: 2026-05-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c8a9f2b1d3e4"
down_revision: tuple = ("5c4e5a090ea6", "a1b2c3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Users: add role column ---
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="developer"))

    # --- Scans: add diff_hash, reasoning_level, synthesis_json ---
    op.add_column("scans", sa.Column("diff_hash", sa.String(64), nullable=True))
    op.add_column("scans", sa.Column("reasoning_level", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("scans", sa.Column("synthesis_json", postgresql.JSONB(), nullable=True))
    op.create_index("ix_scans_diff_hash", "scans", ["diff_hash"])

    # --- ScanFindings: add reasoning column ---
    op.add_column("scan_findings", sa.Column("reasoning", sa.Text(), nullable=True))

    # --- ScanMetrics table ---
    op.create_table(
        "scan_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("total_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("regex_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("entropy_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ner_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("llm_calls_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reasoning_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("findings_before_dedup", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_after_dedup", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_savings_usd", sa.Float(), nullable=False, server_default="0.0"),
    )

    # --- DeveloperScores table ---
    op.create_table(
        "developer_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("total_scans", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clean_scan_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clean_scan_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("critical_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("medium_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_per_scan", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("weighted_finding_density", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("feedback_given_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feedback_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("improvement_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("security_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("responsiveness_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("improvement_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("composite_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "period_start", name="uq_user_period"),
    )


def downgrade() -> None:
    op.drop_table("developer_scores")
    op.drop_table("scan_metrics")
    op.drop_column("scan_findings", "reasoning")
    op.drop_index("ix_scans_diff_hash", table_name="scans")
    op.drop_column("scans", "synthesis_json")
    op.drop_column("scans", "reasoning_level")
    op.drop_column("scans", "diff_hash")
    op.drop_column("users", "role")
