"""Drop user role.

Revision ID: 20261121_drop_role
Revises: 7a0bc825f371
"""
from alembic import op
import sqlalchemy as sa


revision = "20261121_drop_role"
down_revision = "7a0bc825f371"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("users", "role")


def downgrade():
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("user", "superadmin", name="user_role"),
            nullable=False,
            server_default="user",
        ),
    )
