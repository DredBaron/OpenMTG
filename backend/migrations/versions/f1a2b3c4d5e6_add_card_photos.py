"""add card_photos table

Revision ID: f1a2b3c4d5e6
Revises: f0a1b2c3d4e5
Create Date: 2026-08-03

"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'f0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'card_photos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collection_entry_id', sa.Integer(),
                  sa.ForeignKey('collection_entries.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('side', sa.String(5), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('collection_entry_id', 'side', name='uq_card_photo_entry_side'),
    )


def downgrade() -> None:
    op.drop_table('card_photos')
