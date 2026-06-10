"""Extend followups for per-user tracking and resolution

Revision ID: 006_extend_followups
Revises: 005_add_task_deadline_text
Create Date: 2026-05-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_extend_followups"
down_revision: Union[str, None] = "005_add_task_deadline_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("followups", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("followups", sa.Column("reason", sa.String(length=128), nullable=True))
    op.add_column(
        "followups",
        sa.Column("status", sa.String(length=50), server_default="open", nullable=False),
    )
    op.add_column("followups", sa.Column("draft_text", sa.Text(), nullable=True))
    op.add_column("followups", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("followups", sa.Column("latest_email_id", sa.Integer(), nullable=True))
    op.add_column("followups", sa.Column("priority_snapshot", sa.String(length=50), nullable=True))

    op.execute(
        """
        UPDATE followups f
        SET user_id = sub.user_id
        FROM (
            SELECT DISTINCT ON (thread_id) thread_id, user_id
            FROM emails
            ORDER BY thread_id, received_at DESC
        ) sub
        WHERE f.thread_id = sub.thread_id AND f.user_id IS NULL
        """
    )

    op.alter_column("followups", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_followups_user_id",
        "followups",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_followups_latest_email_id",
        "followups",
        "emails",
        ["latest_email_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_followups_user_id"), "followups", ["user_id"], unique=False)
    op.create_index(op.f("ix_followups_status"), "followups", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_followups_status"), table_name="followups")
    op.drop_index(op.f("ix_followups_user_id"), table_name="followups")
    op.drop_constraint("fk_followups_latest_email_id", "followups", type_="foreignkey")
    op.drop_constraint("fk_followups_user_id", "followups", type_="foreignkey")
    op.drop_column("followups", "priority_snapshot")
    op.drop_column("followups", "latest_email_id")
    op.drop_column("followups", "resolved_at")
    op.drop_column("followups", "draft_text")
    op.drop_column("followups", "status")
    op.drop_column("followups", "reason")
    op.drop_column("followups", "user_id")
