"""add trade_transfers table

Revision ID: 2cb17909a6b1
Revises: b03eabef7a3a
Create Date: 2026-11-05

"""
from alembic import op
import sqlalchemy as sa

revision = '2cb17909a6b1'
down_revision = 'b03eabef7a3a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New table only: no ALTER on existing tables, so no batch mode is needed on SQLite.
    op.create_table(
        'trade_transfers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.Integer(), nullable=False),
        sa.Column('transferred_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_id', name='uq_trade_transfers_trade_id'),
    )


def downgrade() -> None:
    op.drop_table('trade_transfers')
