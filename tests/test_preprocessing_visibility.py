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


def test_preprocessing_hides_review_and_unlabeled_rows(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "tambang bagus" in html
    assert "tambang merusak" in html
    assert "tambang biasa" in html
    assert "tidak buruk" not in html
    assert "entah apa" not in html


def test_preprocessing_pending_count_includes_review_and_unlabeled(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "Buka Review dan Label (2)" in html


def test_preprocessing_shows_rerun_and_labels_link(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "Hitung Ulang Label Otomatis" in html
    assert "Buka Review dan Label (2)" in html
    assert "<th>Sumber</th>" not in html
    assert "<th>Skor</th>" not in html
    assert "/preprocessing/labels/manual" not in html


def test_preprocessing_keeps_labels_link_when_nothing_is_pending(dataset):
    with dataset.app.app_context():
        row = Dataset(
            user_id=db.session.execute(db.select(User).filter_by(email="visibility@test.local")).scalar_one().id,
            original_filename="clean.csv",
            stored_filename="clean-private.csv",
            file_path="private",
            row_count=1,
            comment_column="isi",
            status="validated",
        )
        db.session.add(row)
        db.session.flush()
        db.session.add(Comment(
            dataset_id=row.id,
            row_number=2,
            comment_text="tambang bagus",
            sentiment_label="Positif",
            label_source="lexicon",
            review_status="accepted",
        ))
        db.session.commit()
        clean_id = row.id
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={clean_id}").data.decode()
    assert "Buka Review dan Label" in html
