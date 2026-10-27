"""Upload now labels the dataset with InSet automatically (no button needed)."""
import io
import os
import shutil
import time
from pathlib import Path

import pytest
from itsdangerous import URLSafeTimedSerializer

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, User

LEXICON_SOURCE = Path(__file__).resolve().parents[1] / "storage" / "lexicon"


@pytest.fixture
def lexicon(tmp_path):
    """Copy the real InSet files so labeling is genuine, not simulated."""
    target = tmp_path / "lexicon"
    target.mkdir()
    for name in ("positive.tsv", "negative.tsv"):
        source = LEXICON_SOURCE / name
        if not source.is_file():
            pytest.skip("Kamus InSet belum tersedia di storage/lexicon")
        shutil.copy(source, target / name)
    return target


def make_app(monkeypatch, tmp_path, lexicon_folder, role="user"):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setenv("LEXICON_FOLDER", str(lexicon_folder))
    app = create_app()
    app.config.update(TESTING=True)
    return app


def login(app, email, password, role="user"):
    client = app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "auto-lexicon-nonce"
    token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("auto-lexicon-nonce")
    if role == "superadmin":
        with app.app_context():
            user = User(full_name="Admin", email=email, role="superadmin")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
    else:
        client.post("/register", data={"full_name": "Peneliti", "email": email,
                                       "password": password, "csrf_token": token})
    assert client.post("/login", data={"email": email, "password": password,
                                       "csrf_token": token}).status_code == 302
    return client, token


def wait_for_job(client, job_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = client.get(f"/preprocessing/jobs/{job_id}").get_json()
        if payload["status"] in ("completed", "failed"):
            return payload
        time.sleep(0.2)
    raise AssertionError(f"job {job_id} tidak selesai dalam {timeout}s")


def prepare(app):
    """Schema for one test; keeps the fixture free of any long-lived session."""
    with app.app_context():
        db.create_all()


def teardown(app):
    with app.app_context():
        db.session.remove()
        db.drop_all()


# Words the InSet lexicon really scores (verified against storage/lexicon).
CSV_BODY = (
    "isi\n"
    "pelayanan mantap dan bermanfaat\n"
    "kondisi buruk dan kotor\n"
    "tambang berjalan\n"
).encode()


def upload(client, token, body, filename="comments.csv", label_column=None):
    data = {"csrf_token": token, "comment_column": "isi", "file": (io.BytesIO(body), filename)}
    if label_column:
        data["label_column"] = label_column
    return client.post("/datasets/upload", data=data, content_type="multipart/form-data")


def test_upload_starts_lexicon_job_automatically(monkeypatch, tmp_path, lexicon):
    app = make_app(monkeypatch, tmp_path, lexicon)
    prepare(app)
    try:
        client, token = login(app, "auto@example.test", "rahasia-kuat-123")
        response = upload(client, token, CSV_BODY)
        assert response.status_code == 302, response.data[:300]
        location = response.headers["Location"]
        assert "job=" in location
        job_id = location.split("job=")[1].split("&")[0]

        job = wait_for_job(client, job_id)
        assert job["status"] == "completed", job

        with app.app_context():
            comments = db.session.execute(db.select(Comment).order_by(Comment.row_number)).scalars().all()
            assert len(comments) == 3
            # The worker visited every row: version recorded on all of them.
            assert all(comment.lexicon_version for comment in comments)
            labels = [comment.sentiment_label for comment in comments]
            assert labels[0] == "Positif"
            assert labels[1] == "Negatif"
            # An ambiguous row stays unlabeled and is queued for review.
            assert labels[2] is None
            assert comments[2].review_status == "review"
    finally:
        teardown(app)


def test_upload_works_when_lexicon_missing(monkeypatch, tmp_path):
    empty = tmp_path / "no-lexicon"
    empty.mkdir()
    app = make_app(monkeypatch, tmp_path, empty)
    prepare(app)
    try:
        client, token = login(app, "nolex@example.test", "rahasia-kuat-123")
        response = upload(client, token, CSV_BODY)
        assert response.status_code == 200, response.data[:300]
        assert b"tanpa label lexicon" in response.data
        with app.app_context():
            dataset = db.session.execute(db.select(Dataset)).scalar_one()
            assert dataset.row_count == 3
            assert db.session.scalar(db.select(db.func.count(Comment.id))) == 3
    finally:
        teardown(app)


def test_imported_manual_labels_are_never_overwritten(monkeypatch, tmp_path, lexicon):
    app = make_app(monkeypatch, tmp_path, lexicon)
    prepare(app)
    try:
        client, token = login(app, "labels@example.test", "rahasia-kuat-123", role="superadmin")
        body = ("isi,kategori\n"
                "kondisi buruk dan kotor,Positif\n"
                "pelayanan mantap dan bermanfaat,Positif\n").encode()
        response = upload(client, token, body, filename="labelled.csv", label_column="kategori")
        assert response.status_code == 302, response.data[:300]
        job_id = response.headers["Location"].split("job=")[1].split("&")[0]
        assert wait_for_job(client, job_id)["status"] == "completed"

        with app.app_context():
            comments = db.session.execute(db.select(Comment).order_by(Comment.row_number)).scalars().all()
            for comment in comments:
                assert comment.manual_label == "Positif"
                assert comment.sentiment_label == "Positif"
                assert comment.label_source == "manual"
                # STRICT.md C3: the lexicon never touches a manual row.
                assert comment.lexicon_version is None
    finally:
        teardown(app)
