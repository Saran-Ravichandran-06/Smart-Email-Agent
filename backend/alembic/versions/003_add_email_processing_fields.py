"""Add email processing fields for cleaned content

Revision ID: 003_add_email_processing_fields
Revises: 002_add_oauth_tokens
Create Date: 2026-05-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_email_processing_fields"
down_revision: Union[str, None] = "002_add_oauth_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("emails", sa.Column("recipient", sa.String(length=512), nullable=True))
    op.add_column("emails", sa.Column("body_raw", sa.Text(), nullable=True))
    op.add_column("emails", sa.Column("body_cleaned", sa.Text(), nullable=True))
    op.add_column("emails", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE emails SET body_raw = body WHERE body_raw IS NULL")


def downgrade() -> None:
    op.drop_column("emails", "processed_at")
    op.drop_column("emails", "body_cleaned")
    op.drop_column("emails", "body_raw")
    op.drop_column("emails", "recipient")
