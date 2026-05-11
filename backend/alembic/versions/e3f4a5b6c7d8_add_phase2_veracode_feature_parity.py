"""add phase2 veracode feature parity columns

Revision ID: e3f4a5b6c7d8
Revises: c8a9f2b1d3e4
Create Date: 2026-05-11 14:00:00.000000

Adds:
- scan_findings: cwe_id, cvss_score, cvss_vector, status, assigned_to, resolved_at, sla_deadline
- finding_feedback: expires_at
- policies table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: str = "c8a9f2b1d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- scan_findings: CWE/CVSS classification ---
    op.add_column("scan_findings", sa.Column("cwe_id", sa.String(20), nullable=True))
    op.add_column("scan_findings", sa.Column("cvss_score", sa.Float(), nullable=True))
    op.add_column("scan_findings", sa.Column("cvss_vector", sa.String(200), nullable=True))

    # --- scan_findings: lifecycle management ---
    op.add_column("scan_findings", sa.Column(
        "status", sa.String(20), nullable=False, server_default="new"
    ))
    op.add_column("scan_findings", sa.Column(
        "assigned_to",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.add_column("scan_findings", sa.Column(
        "resolved_at", sa.DateTime(timezone=True), nullable=True
    ))
    op.add_column("scan_findings", sa.Column(
        "sla_deadline", sa.DateTime(timezone=True), nullable=True
    ))

    # --- finding_feedback: expiration support ---
    op.add_column("finding_feedback", sa.Column(
        "expires_at", sa.DateTime(timezone=True), nullable=True
    ))

    # --- policies table ---
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repository", sa.String(500), nullable=False, unique=True, index=True),
        sa.Column("max_severity_allowed", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("required_engines", postgresql.JSONB(), nullable=True),
        sa.Column("sla_overrides", postgresql.JSONB(), nullable=True),
        sa.Column("block_on_sla_breach", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("min_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("policies")

    op.drop_column("finding_feedback", "expires_at")

    op.drop_column("scan_findings", "sla_deadline")
    op.drop_column("scan_findings", "resolved_at")
    op.drop_column("scan_findings", "assigned_to")
    op.drop_column("scan_findings", "status")
    op.drop_column("scan_findings", "cvss_vector")
    op.drop_column("scan_findings", "cvss_score")
    op.drop_column("scan_findings", "cwe_id")
