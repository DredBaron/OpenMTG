"""add settings table

Revision ID: b80639f45416
Revises: ede0c3064869
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'b80639f45416'
down_revision = 'ede0c3064869'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_settings_id', 'settings', ['id'], unique=False)
    op.create_index('ix_settings_key', 'settings', ['key'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_settings_key', table_name='settings')
    op.drop_index('ix_settings_id', table_name='settings')
    op.drop_table('settings')
