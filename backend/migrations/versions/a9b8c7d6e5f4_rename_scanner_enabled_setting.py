"""rename scanner_enabled setting to card_search_enabled

Revision ID: a9b8c7d6e5f4
Revises: f4639b2e6053
Create Date: 2026-07-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = 'f4639b2e6053'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE settings SET key = 'card_search_enabled' WHERE key = 'scanner_enabled'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE settings SET key = 'scanner_enabled' WHERE key = 'card_search_enabled'"
    )
