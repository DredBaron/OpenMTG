"""add is_favorite to collection_entries

Revision ID: c1a2b3d4e5f6
Revises: b80639f45416
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa

revision = 'c1a2b3d4e5f6'
down_revision = 'b80639f45416'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'collection_entries',
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column('collection_entries', 'is_favorite')
