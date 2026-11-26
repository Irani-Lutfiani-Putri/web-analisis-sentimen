"""Add source and comment link to stored predictions.

Revision ID: 20261126_results_predictions
Revises: 20261126_classification_stages
"""
from alembic import op
import sqlalchemy as sa


revision = "20261126_results_predictions"
down_revision = "20261126_classification_stages"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "predictions",
        sa.Column("comment_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "predictions",
        sa.Column(
            "source", sa.String(length=20), nullable=False,
            server_default="testing",
        ),
    )
    op.create_index("ix_predictions_comment_id", "predictions", ["comment_id"])
    op.create_foreign_key(
        "fk_predictions_comment_id", "predictions", "comments",
        ["comment_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_predictions_comment_id", "predictions", type_="foreignkey")
    op.drop_index("ix_predictions_comment_id", table_name="predictions")
    op.drop_column("predictions", "source")
    op.drop_column("predictions", "comment_id")
