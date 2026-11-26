"""Add staged classification fields to model runs.

Revision ID: 20261126_classification_stages
Revises: 20261124_preprocess_version
"""
from alembic import op
import sqlalchemy as sa


revision = "20261126_classification_stages"
down_revision = "20261124_preprocess_version"
branch_labels = None
depends_on = None


COLUMNS = (
    ("split_config", sa.JSON()),
    ("split_indices", sa.JSON()),
    ("train_size", sa.Integer()),
    ("test_size", sa.Integer()),
    ("train_distribution", sa.JSON()),
    ("test_distribution", sa.JSON()),
    ("tfidf_vocabulary_size", sa.Integer()),
    ("tfidf_train_shape", sa.JSON()),
    ("tfidf_test_shape", sa.JSON()),
    ("prediction_distribution", sa.JSON()),
    ("test_count", sa.Integer()),
    ("split_at", sa.DateTime()),
    ("tfidf_at", sa.DateTime()),
    ("trained_at", sa.DateTime()),
    ("evaluated_at", sa.DateTime()),
)


def upgrade():
    for name, column_type in COLUMNS:
        op.add_column("model_runs", sa.Column(name, column_type, nullable=True))


def downgrade():
    for name, _ in reversed(COLUMNS):
        op.drop_column("model_runs", name)
