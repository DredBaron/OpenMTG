"""initial trades schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-08-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('initiator_id', sa.Integer(), nullable=False),
        sa.Column('counterpart_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='proposed'),
        sa.Column('initiator_confirmed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('counterpart_confirmed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('last_actor_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_trades_initiator_id', 'trades', ['initiator_id'])
    op.create_index('ix_trades_counterpart_id', 'trades', ['counterpart_id'])

    op.create_table(
        'trade_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('trade_id', sa.Integer(), sa.ForeignKey('trades.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('collection_entry_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('card_snapshot_name', sa.String(255)),
        sa.Column('card_snapshot_image', sa.String(512)),
        sa.Column('card_snapshot_price', sa.Float()),
        sa.Column('foil', sa.Boolean(), server_default='0'),
        sa.Column('condition', sa.String(10), server_default='NM'),
    )
    op.create_index('ix_trade_items_id', 'trade_items', ['id'])


def downgrade() -> None:
    op.drop_table('trade_items')
    op.drop_table('trades')
