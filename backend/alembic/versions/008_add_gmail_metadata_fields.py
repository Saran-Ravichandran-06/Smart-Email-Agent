"""add gmail metadata fields

Revision ID: 008_add_gmail_metadata_fields
Revises: 007_add_thread_summaries
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "008_add_gmail_metadata_fields"
down_revision = "007_add_thread_summaries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("emails", sa.Column("gmail_history_id", sa.String(length=255), nullable=True))
    op.add_column("emails", sa.Column("cc", sa.String(length=512), nullable=True))
    op.add_column("emails", sa.Column("label_ids", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("emails", "label_ids")
    op.drop_column("emails", "cc")
    op.drop_column("emails", "gmail_history_id")
