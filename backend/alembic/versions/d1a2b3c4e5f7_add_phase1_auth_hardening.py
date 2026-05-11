"""add phase1 auth hardening

Revision ID: d1a2b3c4e5f7
Revises: e3f4a5b6c7d8
Create Date: 2026-05-11 16:00:00.000000

Adds:
- users: failed_login_attempts, locked_until
- refresh_tokens table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d1a2b3c4e5f7"
down_revision: str = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: account lockout fields ---
    op.add_column("users", sa.Column(
        "failed_login_attempts", sa.Integer(), nullable=False, server_default="0"
    ))
    op.add_column("users", sa.Column(
        "locked_until", sa.DateTime(timezone=True), nullable=True
    ))

    # --- refresh_tokens table ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
