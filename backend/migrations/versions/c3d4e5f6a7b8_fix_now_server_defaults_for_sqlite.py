"""fix now() server defaults for sqlite compatibility

Revision ID: c3d4e5f6a7b8
Revises: f1a2b3c4d5e6
Create Date: 2026-09-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = [
    ('cards', 'last_fetched'),
    ('users', 'created_at'),
    ('collection_entries', 'added_at'),
    ('decks', 'created_at'),
    ('price_history', 'recorded_at'),
    ('wishlist_entries', 'added_at'),
    ('converted_currencies', 'added_at'),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=True,
                server_default=sa.func.now(),
            )


def downgrade() -> None:
    for table, column in _COLUMNS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=True,
                server_default=sa.text('now()'),
            )
