"""Add thread resolution state tracking.

Revision ID: 013_thread_states
Revises: 012_oauth_token_scopes
Create Date: 2026-06-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013_thread_states"
down_revision: str | None = "012_oauth_token_scopes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "thread_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="open", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "thread_id", name="uq_thread_states_user_thread"),
    )
    op.create_index(op.f("ix_thread_states_user_id"), "thread_states", ["user_id"], unique=False)
    op.create_index(op.f("ix_thread_states_thread_id"), "thread_states", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_thread_states_thread_id"), table_name="thread_states")
    op.drop_index(op.f("ix_thread_states_user_id"), table_name="thread_states")
    op.drop_table("thread_states")
