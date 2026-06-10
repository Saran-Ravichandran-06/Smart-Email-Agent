"""Drop thread_summaries table

Revision ID: 009_drop_thread_summaries
Revises: 008_add_gmail_metadata_fields
Create Date: 2026-06-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_drop_thread_summaries"
down_revision: Union[str, None] = "008_add_gmail_metadata_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_thread_summaries_user_id"), table_name="thread_summaries")
    op.drop_index(op.f("ix_thread_summaries_thread_id"), table_name="thread_summaries")
    op.drop_table("thread_summaries")


def downgrade() -> None:
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "thread_id", name="uq_thread_summaries_user_thread"),
    )
    op.create_index(op.f("ix_thread_summaries_thread_id"), "thread_summaries", ["thread_id"], unique=False)
    op.create_index(op.f("ix_thread_summaries_user_id"), "thread_summaries", ["user_id"], unique=False)
