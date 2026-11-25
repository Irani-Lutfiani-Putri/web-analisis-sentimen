"""Add preprocessing version to comments.

Revision ID: 20261124_preprocess_version
Revises: 20261121_drop_role
"""
from alembic import op
import sqlalchemy as sa


revision = "20261124_preprocess_version"
down_revision = "20261121_drop_role"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "comments",
        sa.Column("preprocessing_version", sa.String(length=50), nullable=True),
    )


def downgrade():
    op.drop_column("comments", "preprocessing_version")
