"""add loan fields to collection_entries

Revision ID: f0a1b2c3d4e5
Revises: a9b8c7d6e5f4
Create Date: 2026-08-03

"""
from alembic import op
import sqlalchemy as sa

revision = 'f0a1b2c3d4e5'
down_revision = 'a9b8c7d6e5f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'collection_entries',
        sa.Column('on_loan', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column(
        'collection_entries',
        sa.Column('loaned_to', sa.Text(), nullable=True)
    )
    op.add_column(
        'collection_entries',
        sa.Column('loan_date', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('collection_entries', 'loan_date')
    op.drop_column('collection_entries', 'loaned_to')
    op.drop_column('collection_entries', 'on_loan')
