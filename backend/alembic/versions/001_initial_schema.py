"""Initial schema: users, emails, tasks, followups

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-05-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("google_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gmail_message_id", sa.String(length=255), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("sender", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gmail_message_id"),
    )
    op.create_index(
        op.f("ix_emails_gmail_message_id"),
        "emails",
        ["gmail_message_id"],
        unique=False,
    )
    op.create_index(op.f("ix_emails_thread_id"), "emails", ["thread_id"], unique=False)
    op.create_index(op.f("ix_emails_user_id"), "emails", ["user_id"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email_id", sa.Integer(), nullable=False),
        sa.Column("task_text", sa.Text(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_email_id"), "tasks", ["email_id"], unique=False)

    op.create_table(
        "followups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "needs_followup",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_followups_thread_id"),
        "followups",
        ["thread_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_followups_thread_id"), table_name="followups")
    op.drop_table("followups")
    op.drop_index(op.f("ix_tasks_email_id"), table_name="tasks")
    op.drop_table("tasks")
    op.drop_index(op.f("ix_emails_user_id"), table_name="emails")
    op.drop_index(op.f("ix_emails_thread_id"), table_name="emails")
    op.drop_index(op.f("ix_emails_gmail_message_id"), table_name="emails")
    op.drop_table("emails")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
