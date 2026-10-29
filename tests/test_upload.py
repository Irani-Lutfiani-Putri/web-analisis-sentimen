import io
import os
import pytest
from itsdangerous import URLSafeTimedSerializer
from app import create_app
from app.extensions import db
from app.models import Dataset, Comment


@pytest.fixture
def client(monkeypatch, tmp_path):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path / "uploads"))
    # Empty lexicon folder: these tests cover the import path without auto-labeling.
    monkeypatch.setenv("LEXICON_FOLDER", str(tmp_path / "lexicon-empty"))
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        web = app.test_client()
        with web.session_transaction() as session:
            session["csrf_token"] = "test-upload-nonce"
        token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("test-upload-nonce")
        web.post("/register", data={"full_name":"Peneliti", "email":"upload@example.test", "password":"rahasia-kuat-123", "csrf_token":token})
        web.post("/login", data={"email":"upload@example.test", "password":"rahasia-kuat-123", "csrf_token":token})
        yield web, token
        db.session.remove()
        db.drop_all()


def test_upload_saves_actual_rows_to_mysql(client):
    web, token = client
    response = web.post("/datasets/upload", data={"csrf_token":token, "comment_column":"isi", "file":(io.BytesIO(b"isi\nTambang berjalan\nTidak ada komentar\n"),"comments.csv")}, content_type="multipart/form-data")
    assert response.status_code == 200
    assert b"2 komentar tersimpan" in response.data
    with web.application.app_context():
        dataset = db.session.execute(db.select(Dataset)).scalar_one()
        assert dataset.row_count == 2
        assert db.session.execute(db.select(Comment)).scalars().all()[0].manual_label is None


def test_user_cannot_import_manual_labels(client):
    web, token = client
    response = web.post("/datasets/upload", data={"csrf_token":token, "comment_column":"isi", "label_column":"kategori", "file":(io.BytesIO(b"isi,kategori\nTambang berjalan,Positif\n"),"comments.csv")}, content_type="multipart/form-data")
    assert response.status_code == 403
    with web.application.app_context():
        assert db.session.execute(db.select(Dataset)).first() is None


def test_upload_rejects_missing_column(client):
    web, token = client
    response = web.post("/datasets/upload", data={"csrf_token":token, "comment_column":"komentar", "file":(io.BytesIO(b"isi\nTambang berjalan\n"),"comments.csv")}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert b"Kolom komentar" in response.data
    assert b'id="upload_comment_column-error"' in response.data
    assert b'aria-invalid="true"' in response.data


def test_upload_rejects_bad_encoding(client):
    web, token = client
    response = web.post("/datasets/upload", data={"csrf_token":token, "comment_column":"isi", "file":(io.BytesIO(b"isi\n\xff"),"comments.csv")}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert b"UTF-8" in response.data
    assert b'id="upload_file-error"' in response.data


def test_upload_rejects_wrong_extension(client):
    web, token = client
    response = web.post("/datasets/upload", data={"csrf_token":token, "comment_column":"isi", "file":(io.BytesIO(b"isi\nTambang"),"comments.txt")}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert b'id="upload_file-error"' in response.data
    with web.application.app_context():
        assert db.session.execute(db.select(Dataset)).first() is None
