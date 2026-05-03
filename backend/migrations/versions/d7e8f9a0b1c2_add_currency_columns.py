"""add currency columns

Revision ID: d7e8f9a0b1c2
Revises: c1a2b3d4e5f6
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa

revision = 'd7e8f9a0b1c2'
down_revision = 'c1a2b3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cards',
        sa.Column('price_eur_foil', sa.Float(), nullable=True)
    )
    op.add_column('users',
        sa.Column('preferred_currency', sa.String(), nullable=False, server_default='usd')
    )


def downgrade():
    op.drop_column('cards', 'price_eur_foil')
    op.drop_column('users', 'preferred_currency')