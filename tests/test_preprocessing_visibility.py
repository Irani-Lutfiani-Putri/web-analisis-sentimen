import os
from types import SimpleNamespace

import pytest
from itsdangerous import URLSafeTimedSerializer

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, User


@pytest.fixture
def dataset(monkeypatch):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        user = User(full_name="Peneliti", email="visibility@test.local")
        user.set_password("secure-password-123")
        db.session.add(user)
        db.session.flush()
        row = Dataset(
            user_id=user.id,
            original_filename="visibility.csv",
            stored_filename="visibility-private.csv",
            file_path="private",
            row_count=5,
            comment_column="isi",
            status="validated",
        )
        db.session.add(row)
        db.session.flush()
        rows = [
            ("tambang bagus", "Positif", "lexicon", "accepted"),
            ("tambang merusak", "Negatif", "lexicon", "accepted"),
            ("tambang biasa", "Netral", "lexicon", "accepted"),
            ("tidak buruk", None, "review", "review"),
            ("entah apa", None, None, None),
        ]
        for index, (text, label, source, review) in enumerate(rows, start=2):
            db.session.add(
                Comment(
                    dataset_id=row.id,
                    row_number=index,
                    comment_text=text,
                    sentiment_label=label,
                    label_source=source,
                    review_status=review,
                    lexicon_score=1 if label else None,
                )
            )
        db.session.commit()
        payload = SimpleNamespace(app=app, id=row.id)
    yield payload
    with app.app_context():
        db.session.remove()
        db.drop_all()


def login(app, email):
    client = app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "visibility-nonce"
    token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("visibility-nonce")
    response = client.post(
        "/login",
        data={"email": email, "password": "secure-password-123", "csrf_token": token},
    )
    assert response.status_code == 302
    return client


def test_preprocessing_shows_stages_without_comment_table(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "Cleaning" in html
    assert "Case Folding" in html
    assert "Tokenizing" in html
    assert "Stopword Removal" in html
    assert "Stemming" in html
    assert "Jalankan Preprocessing" in html
    assert "Download" not in html
    assert "Lanjut ke Klasifikasi" not in html
    assert "tambang bagus" not in html
    assert "tidak buruk" not in html
    assert "entah apa" not in html


def test_preprocessing_comparison_shows_each_stage(dataset):
    with dataset.app.app_context():
        comment = db.session.execute(
            db.select(Comment).filter_by(dataset_id=dataset.id, comment_text="tambang bagus")
        ).scalar_one()
        comment.cleaned_text = "tambang bagus"
        db.session.get(Dataset, dataset.id).status = "processed"
        db.session.commit()
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    for header in (
        "Komentar asli", "Cleaning", "Case Folding", "Tokenizing",
        "Normalisasi Kata", "Stopword Removal", "Stemming", "Label",
    ):
        assert header in html
    assert "tambang | bagus" in html
    assert "Download" not in html
    assert "Lanjut ke Klasifikasi" in html
    assert f"/classification?dataset_id={dataset.id}" in html


def test_preprocessing_hides_review_and_labeling_links(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "Buka Review dan Label" not in html
    assert "Buka Pelabelan Otomatis" not in html
    assert "Hitung Ulang Label Otomatis" not in html


def test_preprocessing_hides_label_metadata(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "<th>Sumber</th>" not in html
    assert "<th>Skor</th>" not in html
    assert "/preprocessing/labels/manual" not in html


def test_labeling_page_shows_counts_and_rerun(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing/labeling?dataset_id={dataset.id}").data.decode()
    assert "Hitung Ulang Label Otomatis" in html
    assert "Buka Review dan Label (2)" in html
    assert "2 komentar menunggu label manual" in html
    assert "Kembali ke Preprocessing" in html


def test_preprocessing_never_shows_labels_link(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "Buka Review dan Label" not in html


def test_preprocessing_rejects_duplicate_run(dataset, monkeypatch):
    dataset.app.config["WTF_CSRF_ENABLED"] = False
    client = login(dataset.app, "visibility@test.local")
    monkeypatch.setattr("app.routes.preprocessing.is_processing", lambda _: True)
    response = client.post("/preprocessing/run", data={"dataset_id": dataset.id})
    assert response.status_code == 409
    assert b"sedang berjalan" in response.data
