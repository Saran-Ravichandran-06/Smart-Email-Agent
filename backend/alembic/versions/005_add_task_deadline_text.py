"""Add deadline_text to tasks for natural-language deadlines

Revision ID: 005_add_task_deadline_text
Revises: 004_add_email_priority_index
Create Date: 2026-05-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_add_task_deadline_text"
down_revision: Union[str, None] = "004_add_email_priority_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("deadline_text", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "deadline_text")
