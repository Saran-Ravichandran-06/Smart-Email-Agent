"""Add thread_summaries table

Revision ID: 007_add_thread_summaries
Revises: 006_extend_followups
Create Date: 2026-05-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_add_thread_summaries"
down_revision: Union[str, None] = "006_extend_followups"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "thread_summaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_decisions", sa.Text(), nullable=True),
        sa.Column("pending_tasks", sa.Text(), nullable=True),
        sa.Column("deadlines", sa.Text(), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "thread_id", name="uq_thread_summaries_user_thread"),
    )
    op.create_index(
        op.f("ix_thread_summaries_thread_id"),
        "thread_summaries",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_thread_summaries_user_id"),
        "thread_summaries",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_thread_summaries_user_id"), table_name="thread_summaries")
    op.drop_index(op.f("ix_thread_summaries_thread_id"), table_name="thread_summaries")
    op.drop_table("thread_summaries")
