"""add webhook_credentials table and wishlist notified flag

Revision ID: a3b4c5d6e7f8
Revises: c3d4e5f6a7b8
Create Date: 2026-09-11

"""
from alembic import op
import sqlalchemy as sa

revision = 'a3b4c5d6e7f8'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'webhook_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('webhook_id', sa.String(length=64), nullable=False),
        sa.Column('secret_hash', sa.String(length=64), nullable=False),
        sa.Column('target_url', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_webhook_credentials_id'), 'webhook_credentials', ['id'], unique=False
    )
    op.create_index(
        op.f('ix_webhook_credentials_webhook_id'), 'webhook_credentials', ['webhook_id'], unique=True
    )

    op.add_column(
        'wishlist_entries',
        sa.Column('notified', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column('wishlist_entries', 'notified')
    op.drop_index('ix_webhook_credentials_id', table_name='webhook_credentials')
    op.drop_index('ix_webhook_credentials_webhook_id', table_name='webhook_credentials')
    op.drop_table('webhook_credentials')
