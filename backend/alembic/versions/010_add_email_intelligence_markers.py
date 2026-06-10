"""Add email intelligence processing markers

Revision ID: 010_email_intel_markers
Revises: 009_drop_thread_summaries
Create Date: 2026-06-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010_email_intel_markers"
down_revision: Union[str, None] = "009_drop_thread_summaries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("emails", sa.Column("task_extracted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("emails", sa.Column("followup_evaluated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("emails", "followup_evaluated_at")
    op.drop_column("emails", "task_extracted_at")
