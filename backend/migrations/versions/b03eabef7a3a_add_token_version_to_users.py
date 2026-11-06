"""add token_version to users

Revision ID: b03eabef7a3a
Revises: b4c5d6e7f8a9
Create Date: 2026-11-05

"""
from alembic import op
import sqlalchemy as sa

revision = 'b03eabef7a3a'
down_revision = 'b4c5d6e7f8a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('token_version')
