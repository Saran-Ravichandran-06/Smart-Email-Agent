"""Add stored OAuth scope metadata.

Revision ID: 012_oauth_token_scopes
Revises: 011_send_sync_meta
Create Date: 2026-06-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012_oauth_token_scopes"
down_revision: str | None = "011_send_sync_meta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("oauth_tokens", sa.Column("scopes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("oauth_tokens", "scopes")
