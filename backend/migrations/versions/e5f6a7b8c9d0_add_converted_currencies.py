"""add converted_currencies

Revision ID: e5f6a7b8c9d0
Revises: a1b2c3d4e5f6
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'converted_currencies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False),
        sa.Column('rate', sa.Float(), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('rate_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_converted_currency_code'),
    )
    op.create_index(op.f('ix_converted_currencies_id'), 'converted_currencies', ['id'], unique=False)
    op.create_index(op.f('ix_converted_currencies_code'), 'converted_currencies', ['code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_converted_currencies_code'), table_name='converted_currencies')
    op.drop_index(op.f('ix_converted_currencies_id'), table_name='converted_currencies')
    op.drop_table('converted_currencies')
