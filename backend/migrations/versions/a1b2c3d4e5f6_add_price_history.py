"""add price_history table

Revision ID: a1b2c3d4e5f6
Revises: f4639b2e6053
Create Date: 2026-05-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f4639b2e6053'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('card_id', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('price_usd', sa.Float(), nullable=True),
        sa.Column('price_usd_foil', sa.Float(), nullable=True),
        sa.Column('price_eur', sa.Float(), nullable=True),
        sa.Column('price_eur_foil', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['card_id'], ['cards.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_price_history_id'), 'price_history', ['id'], unique=False)
    op.create_index(op.f('ix_price_history_card_id'), 'price_history', ['card_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_price_history_card_id'), table_name='price_history')
    op.drop_index(op.f('ix_price_history_id'), table_name='price_history')
    op.drop_table('price_history')
