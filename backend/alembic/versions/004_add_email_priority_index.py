"""Add index on emails.priority for filtering

Revision ID: 004_add_email_priority_index
Revises: 003_add_email_processing_fields
Create Date: 2026-05-16

"""

from typing import Sequence, Union

from alembic import op

revision: str = "004_add_email_priority_index"
down_revision: Union[str, None] = "003_add_email_processing_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_emails_priority"), "emails", ["priority"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_emails_priority"), table_name="emails")
