import os
from types import SimpleNamespace

import pytest
from itsdangerous import URLSafeTimedSerializer

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, LabelHistory, User


@pytest.fixture
def page(monkeypatch):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        owner = User(full_name="Pemilik", email="a@test.local")
        owner.set_password("secure-password-123")
        other = User(full_name="Lain", email="b@test.local")
        other.set_password("secure-password-123")
        db.session.add_all([owner, other])
        db.session.flush()
        dataset = Dataset(
            user_id=owner.id,
            original_filename="labels.csv",
            stored_filename="labels-private.csv",
            file_path="private",
            row_count=4,
            comment_column="isi",
            status="validated",
        )
        db.session.add(dataset)
        db.session.flush()
        rows = [
            ("tambang bagus", "Positif", "lexicon", "accepted"),
            ("tambang merusak", "Negatif", "lexicon", "accepted"),
            ("tidak buruk", None, "review", "review"),
            ("entah", None, None, None),
        ]
        created = []
        for index, (text, label, source, review) in enumerate(rows, start=2):
            comment = Comment(
                dataset_id=dataset.id,
                row_number=index,
                comment_text=text,
                sentiment_label=label,
                label_source=source,
                review_status=review,
                lexicon_score=1 if label else None,
            )
            db.session.add(comment)
            created.append(comment)
        db.session.commit()
        payload = SimpleNamespace(
            app=app,
            dataset_id=dataset.id,
            accepted_id=created[0].id,
            review_id=created[2].id,
            unlabeled_id=created[3].id,
        )
    yield payload
    with app.app_context():
        db.session.remove()
        db.drop_all()


def login(app, email):
    client = app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "labels-nonce"
    token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("labels-nonce")
    response = client.post(
        "/login",
        data={"email": email, "password": "secure-password-123", "csrf_token": token},
    )
    assert response.status_code == 302
    return client, token


def test_login_required(page):
    response = page.app.test_client().get("/labels")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_labels_defaults_to_review_and_includes_unlabeled(page):
    client, _ = login(page.app, "a@test.local")
    html = client.get(f"/labels?dataset_id={page.dataset_id}").data.decode()
    assert "tidak buruk" in html
    assert "entah" in html
    assert "tambang bagus" not in html
    assert 'value="review" selected' in html


def test_labels_filter_list(page):
    client, _ = login(page.app, "a@test.local")
    html = client.get(f"/labels?dataset_id={page.dataset_id}").data.decode()
    for key in ("semua", "sudah", "positif", "negatif", "netral", "review", "manual", "lexicon"):
        assert f'value="{key}"' in html


def test_save_label_writes_history(page):
    client, token = login(page.app, "a@test.local")
    response = client.post("/labels/label", data={
        "csrf_token": token, "comment_id": page.review_id, "label": "Netral",
    })
    assert response.status_code == 302
    with page.app.app_context():
        comment = db.session.get(Comment, page.review_id)
        assert comment.manual_label == "Netral"
        assert comment.sentiment_label == "Netral"
        assert comment.label_source == "manual"
        assert db.session.scalar(db.select(db.func.count(LabelHistory.id))) == 1


def test_manual_label_returns_to_same_page_and_query(page):
    client, token = login(page.app, "a@test.local")
    response = client.post("/labels/label", data={
        "csrf_token": token,
        "comment_id": page.review_id,
        "label": "Positif",
        "q": "merusak",
        "page": "2",
    })
    assert response.status_code == 302
    assert "q=merusak" in response.headers["Location"]
    assert "page=2" in response.headers["Location"]


def test_bulk_label_applies_to_selected_rows(page):
    client, token = login(page.app, "a@test.local")
    response = client.post("/labels/label/bulk", data={
        "csrf_token": token,
        "dataset_id": page.dataset_id,
        "label": "Negatif",
        "comment_ids": [str(page.review_id), str(page.unlabeled_id)],
    })
    assert response.status_code == 302
    with page.app.app_context():
        rows = db.session.execute(
            db.select(Comment).filter(Comment.id.in_([page.review_id, page.unlabeled_id]))
        ).scalars().all()
        assert all(row.manual_label == "Negatif" for row in rows)


def test_holdout_requires_manual_label(page):
    client, token = login(page.app, "a@test.local")
    response = client.post("/labels/holdout", data={
        "csrf_token": token, "comment_id": page.review_id, "value": "1",
    })
    assert response.status_code == 302
    assert "error=" in response.headers["Location"]
    with page.app.app_context():
        assert db.session.get(Comment, page.review_id).is_independent_holdout is False


def test_holdout_toggle_after_label(page):
    client, token = login(page.app, "a@test.local")
    client.post("/labels/label", data={
        "csrf_token": token, "comment_id": page.review_id, "label": "Positif",
    })
    client.post("/labels/holdout", data={
        "csrf_token": token, "comment_id": page.review_id, "value": "1",
    })
    with page.app.app_context():
        assert db.session.get(Comment, page.review_id).is_independent_holdout is True


def test_other_account_cannot_label_foreign_comment(page):
    client, token = login(page.app, "b@test.local")
    response = client.post("/labels/label", data={
        "csrf_token": token, "comment_id": page.review_id, "label": "Positif",
    })
    assert response.status_code == 404


def test_legacy_admin_datasets_redirects(page):
    client, _ = login(page.app, "a@test.local")
    response = client.get(f"/admin/datasets?dataset_id={page.dataset_id}")
    assert response.status_code == 302
    assert "/labels" in response.headers["Location"]
