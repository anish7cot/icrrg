"""add eval_runs and finding_feedback tables

Revision ID: a1b2c3d4e5f6
Revises: bac7655602fc
Create Date: 2026-04-20 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "a1b2c3d4e5f6"
down_revision = "bac7655602fc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("engine", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=True),
        sa.Column("precision", sa.Float, nullable=False),
        sa.Column("recall", sa.Float, nullable=False),
        sa.Column("f1", sa.Float, nullable=False),
        sa.Column("tp_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fp_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fn_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_scenarios", sa.Integer, nullable=False, server_default="0"),
        sa.Column("details_json", JSONB, nullable=True),
    )

    op.create_table(
        "finding_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("scan_finding_id", UUID(as_uuid=True), sa.ForeignKey("scan_findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
    )

    op.create_index("ix_finding_feedback_finding_user", "finding_feedback", ["scan_finding_id", "user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_finding_feedback_finding_user", "finding_feedback")
    op.drop_table("finding_feedback")
    op.drop_table("eval_runs")
