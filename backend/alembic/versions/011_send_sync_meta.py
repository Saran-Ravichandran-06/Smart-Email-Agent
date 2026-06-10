"""Add Gmail send and mailbox sync metadata.

Revision ID: 011_send_sync_meta
Revises: 010_email_intel_markers
Create Date: 2026-06-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011_send_sync_meta"
down_revision: str | None = "010_email_intel_markers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("emails", sa.Column("gmail_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("emails", sa.Column("gmail_deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("emails", sa.Column("reply_sent_message_id", sa.String(length=255), nullable=True))
    op.add_column("emails", sa.Column("reply_sent_thread_id", sa.String(length=255), nullable=True))
    op.add_column("emails", sa.Column("reply_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("emails", sa.Column("reply_sent_body", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("emails", "reply_sent_body")
    op.drop_column("emails", "reply_sent_at")
    op.drop_column("emails", "reply_sent_thread_id")
    op.drop_column("emails", "reply_sent_message_id")
    op.drop_column("emails", "gmail_deleted_at")
    op.drop_column("emails", "gmail_synced_at")
