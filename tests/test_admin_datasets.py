"""Kelola Dataset is Superadmin-only and writes through the existing services."""
import os

import pytest
from itsdangerous import URLSafeTimedSerializer

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, LabelHistory, User


@pytest.fixture
def admin_page(monkeypatch):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        admin = User(full_name="Admin", email="kelola-admin@test.local", role="superadmin")
        admin.set_password("secure-password-123")
        plain = User(full_name="User", email="kelola-user@test.local", role="user")
        plain.set_password("secure-password-123")
        db.session.add_all([admin, plain])
        db.session.flush()

        dataset = Dataset(user_id=admin.id, original_filename="kelola.csv",
                          stored_filename="kelola-private.csv", file_path="private",
                          row_count=4, comment_column="isi", status="validated")
        db.session.add(dataset)
        db.session.flush()
        rows = [
            ("tambang bagus", "Positif", "lexicon", "accepted"),
            ("tambang merusak", "Negatif", "lexicon", "accepted"),
            ("tidak buruk", None, "review", "review"),
            ("entah", None, "review", "review"),
        ]
        for index, (text, label, source, review) in enumerate(rows, start=2):
            db.session.add(Comment(dataset_id=dataset.id, row_number=index, comment_text=text,
                                   sentiment_label=label, label_source=source,
                                   review_status=review, lexicon_score=1))
        db.session.commit()
        ids = [c.id for c in db.session.execute(
            db.select(Comment).filter_by(dataset_id=dataset.id).order_by(Comment.row_number)).scalars()]
        dataset_id = dataset.id
    # Yield outside the app context so later commits are visible to requests.
    yield app, dataset_id, ids
    with app.app_context():
        db.session.remove()
        db.drop_all()


def login(app, email, password="secure-password-123"):
    client = app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "kelola-nonce"
    token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("kelola-nonce")
    assert client.post("/login", data={"email": email, "password": password,
                                       "csrf_token": token}).status_code == 302
    return client, token


def test_regular_user_cannot_open_kelola_dataset(admin_page):
    app, dataset_id, _ = admin_page
    client, token = login(app, "kelola-user@test.local")
    assert client.get("/admin/datasets").status_code == 403
    assert client.post("/admin/datasets/label",
                       data={"csrf_token": token, "comment_id": 1, "label": "Positif"}).status_code == 403
    assert client.post("/admin/datasets/holdout",
                       data={"csrf_token": token, "comment_id": 1, "value": "1"}).status_code == 403


def test_superadmin_sees_full_filter_list_and_thead_legend(admin_page):
    app, dataset_id, _ = admin_page
    client, _ = login(app, "kelola-admin@test.local")
    response = client.get(f"/admin/datasets?dataset_id={dataset_id}")
    assert response.status_code == 200
    html = response.data.decode()
    for key in ("semua", "sudah", "positif", "negatif", "netral", "review", "manual", "lexicon"):
        assert f'value="{key}"' in html
    assert "<th>Status</th>" in html
    assert "<th>Sumber</th>" in html
    assert "perlu review Superadmin" in html
    assert "Kelola Dataset" in html


def test_review_filter_shows_only_pending_rows(admin_page):
    app, dataset_id, _ = admin_page
    client, _ = login(app, "kelola-admin@test.local")
    html = client.get(f"/admin/datasets?dataset_id={dataset_id}&label=review").data.decode()
    assert "2 komentar cocok" in html
    assert "tidak buruk" in html
    assert "tambang bagus" not in html


def test_save_label_writes_history_and_keeps_manual_authority(admin_page):
    app, dataset_id, ids = admin_page
    review_comment_id = ids[2]
    client, token = login(app, "kelola-admin@test.local")
    response = client.post("/admin/datasets/label",
                           data={"csrf_token": token, "comment_id": review_comment_id, "label": "Netral"})
    assert response.status_code == 302
    with app.app_context():
        comment = db.session.get(Comment, review_comment_id)
        assert comment.manual_label == "Netral"
        assert comment.sentiment_label == "Netral"
        assert comment.label_source == "manual"
        history = db.session.execute(db.select(LabelHistory)).scalars().all()
        assert len(history) == 1
        assert history[0].new_label == "Netral"


def test_invalid_label_is_reported_not_crashed(admin_page):
    app, dataset_id, ids = admin_page
    client, token = login(app, "kelola-admin@test.local")
    response = client.post("/admin/datasets/label",
                           data={"csrf_token": token, "comment_id": ids[0], "label": "Sangat Bagus"})
    assert response.status_code == 302
    assert "error=" in response.headers["Location"]
    with app.app_context():
        assert db.session.execute(db.select(LabelHistory)).first() is None


def test_bulk_label_applies_to_selected_rows(admin_page):
    app, dataset_id, ids = admin_page
    client, token = login(app, "kelola-admin@test.local")
    response = client.post("/admin/datasets/label/bulk",
                           data={"csrf_token": token, "dataset_id": dataset_id, "label": "Negatif",
                                 "comment_ids": [str(ids[2]), str(ids[3])]})
    assert response.status_code == 302
    with app.app_context():
        updated = db.session.execute(db.select(Comment).filter(Comment.id.in_([ids[2], ids[3]]))).scalars().all()
        assert all(comment.manual_label == "Negatif" for comment in updated)
        assert db.session.scalar(db.select(db.func.count(LabelHistory.id))) == 2


def test_holdout_requires_manual_label_first(admin_page):
    app, dataset_id, ids = admin_page
    client, token = login(app, "kelola-admin@test.local")
    response = client.post("/admin/datasets/holdout",
                           data={"csrf_token": token, "comment_id": ids[2], "value": "1"})
    assert response.status_code == 302
    assert "error=" in response.headers["Location"]
    with app.app_context():
        assert db.session.get(Comment, ids[2]).is_independent_holdout is False


def test_holdout_toggle_after_labeling(admin_page):
    app, dataset_id, ids = admin_page
    client, token = login(app, "kelola-admin@test.local")
    comment_id = ids[0]
    client.post("/admin/datasets/label",
                data={"csrf_token": token, "comment_id": comment_id, "label": "Positif"})
    response = client.post("/admin/datasets/holdout",
                           data={"csrf_token": token, "comment_id": comment_id, "value": "1"})
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Comment, comment_id).is_independent_holdout is True
    client.post("/admin/datasets/holdout",
                data={"csrf_token": token, "comment_id": comment_id, "value": "0"})
    with app.app_context():
        assert db.session.get(Comment, comment_id).is_independent_holdout is False
