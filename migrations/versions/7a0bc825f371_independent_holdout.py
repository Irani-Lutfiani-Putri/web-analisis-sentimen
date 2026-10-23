"""Require explicit independent holdout provenance.

Revision ID: 7a0bc825f371
Revises: ff1d85f3da51
"""
from alembic import op
import sqlalchemy as sa

revision = '7a0bc825f371'
down_revision = 'ff1d85f3da51'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('comments', sa.Column('is_independent_holdout', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('comments', 'is_independent_holdout', server_default=None)


def downgrade():
    op.drop_column('comments', 'is_independent_holdout')
