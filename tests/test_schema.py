import os
import pytest
from sqlalchemy import inspect
from app import create_app
from app.extensions import db


def test_required_tables_and_comment_constraints(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        assert {"users", "datasets", "comments", "model_runs", "predictions", "label_history"}.issubset(inspector.get_table_names())
        assert any(set(item["column_names"]) == {"dataset_id", "row_number"} for item in inspector.get_unique_constraints("comments"))
        db.drop_all()
