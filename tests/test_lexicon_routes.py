import os
import re
import time

import pytest
from itsdangerous import URLSafeTimedSerializer

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, LabelHistory, User


@pytest.fixture
def setup(monkeypatch):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        owner = User(full_name="Pemilik", email="owner@test.local")
        owner.set_password("secure-password-123")
        other = User(full_name="Lain", email="other@test.local")
        other.set_password("secure-password-123")
        db.session.add_all([owner, other])
        db.session.flush()
        dataset = Dataset(
            user_id=owner.id,
            original_filename="uji.csv",
            stored_filename="uji-private.csv",
            file_path="private",
            row_count=1,
            comment_column="isi",
            status="validated",
        )
        db.session.add(dataset)
        db.session.flush()
        comment = Comment(
            dataset_id=dataset.id,
            row_number=2,
            comment_text="tidak buruk",
            lexicon_score=-3,
            label_source="review",
            review_status="review",
        )
        db.session.add(comment)
        db.session.commit()
        dataset_id, comment_id = dataset.id, comment.id
    yield app, dataset_id, comment_id
    with app.app_context():
        db.session.remove()
        db.drop_all()


def logged_in(app, email):
    client = app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "lexicon-nonce"
    token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("lexicon-nonce")
    response = client.post(
        "/login",
        data={"email": email, "password": "secure-password-123", "csrf_token": token},
    )
    assert response.status_code == 302, response.data.decode()[:200]
    return client, token


def test_account_can_open_labels(setup):
    app, dataset_id, _ = setup
    client, _ = logged_in(app, "owner@test.local")
    response = client.get(f"/labels?dataset_id={dataset_id}")
    assert response.status_code == 200
    assert b"tidak buruk" in response.data


def test_other_account_cannot_run_lexicon_on_dataset(setup):
    app, dataset_id, _ = setup
    client, token = logged_in(app, "other@test.local")
    response = client.post(
        "/preprocessing/lexicon/run",
        data={"csrf_token": token, "dataset_id": dataset_id},
    )
    assert response.status_code == 404


def test_other_account_cannot_label_foreign_comment(setup):
    app, _, comment_id = setup
    client, token = logged_in(app, "other@test.local")
    response = client.post(
        "/labels/label",
        data={"csrf_token": token, "comment_id": comment_id, "label": "Positif"},
    )
    assert response.status_code == 404


def test_invalid_manual_label_is_rejected(setup):
    app, dataset_id, comment_id = setup
    client, token = logged_in(app, "owner@test.local")
    response = client.post(
        "/labels/label",
        data={"csrf_token": token, "comment_id": comment_id, "label": "Sangat Bagus"},
    )
    assert response.status_code == 302
    assert "error=" in response.headers["Location"]
    with app.app_context():
        assert db.session.execute(db.select(LabelHistory)).first() is None


def test_owner_can_label_review_comment(setup):
    app, _, comment_id = setup
    client, token = logged_in(app, "owner@test.local")
    response = client.post(
        "/labels/label",
        data={"csrf_token": token, "comment_id": comment_id, "label": "Positif"},
    )
    assert response.status_code == 302
    with app.app_context():
        comment = db.session.get(Comment, comment_id)
        assert comment.manual_label == "Positif"
        assert db.session.scalar(db.select(db.func.count(LabelHistory.id))) == 1


def test_lexicon_rerun_uses_background_job(setup):
    app, dataset_id, comment_id = setup
    client, token = logged_in(app, "owner@test.local")
    response = client.post(
        "/preprocessing/lexicon/run",
        data={"csrf_token": token, "dataset_id": dataset_id},
    )
    assert response.status_code == 302
    job = re.search(r"job=([0-9a-f]{32})", response.headers.get("Location", ""))
    assert job, response.headers.get("Location")
    deadline = time.time() + 60
    status = {}
    while time.time() < deadline:
        status = client.get(f"/preprocessing/jobs/{job.group(1)}").get_json() or {}
        if status.get("status") in ("completed", "failed"):
            break
        time.sleep(0.5)
    assert status.get("status") == "completed", status
    with app.app_context():
        assert db.session.get(Comment, comment_id).lexicon_version is not None
