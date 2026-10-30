"""What each role may see: users get four filters and no review rows."""
import os

import pytest
from itsdangerous import URLSafeTimedSerializer

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, User


@pytest.fixture
def roles(monkeypatch):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        admin = User(full_name="Admin", email="role-admin@test.local", role="superadmin")
        admin.set_password("secure-password-123")
        plain = User(full_name="User", email="role-user@test.local", role="user")
        plain.set_password("secure-password-123")
        db.session.add_all([admin, plain])
        db.session.flush()

        dataset = Dataset(user_id=plain.id, original_filename="role.csv",
                          stored_filename="role-private.csv", file_path="private",
                          row_count=5, comment_column="isi", status="validated")
        db.session.add(dataset)
        db.session.flush()

        rows = [
            ("tambang bagus", "Positif", "lexicon", "accepted"),
            ("tambang merusak", "Negatif", "lexicon", "accepted"),
            ("tambang biasa", "Netral", "lexicon", "accepted"),
            ("tidak buruk", None, "review", "review"),
            ("entah apa", None, "review", "review"),
        ]
        for index, (text, label, source, review) in enumerate(rows, start=2):
            db.session.add(Comment(dataset_id=dataset.id, row_number=index, comment_text=text,
                                   sentiment_label=label, label_source=source,
                                   review_status=review, lexicon_score=1))
        db.session.commit()
        dataset_id, plain_id, admin_id = dataset.id, plain.id, admin.id
    # Leave the app context before yielding: a long-lived session would keep a
    # REPEATABLE READ snapshot and hide rows committed by the test body.
    yield app, dataset_id, plain_id, admin_id
    with app.app_context():
        db.session.remove()
        db.drop_all()


def login(app, email, password="secure-password-123"):
    client = app.test_client()
    with client.session_transaction() as session:
        session["csrf_token"] = "role-nonce"
    token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("role-nonce")
    assert client.post("/login", data={"email": email, "password": password,
                                       "csrf_token": token}).status_code == 302
    return client, token


def options_in(html):
    import re
    select = re.search(r'<select id="label".*?</select>', html, re.S)
    assert select, "select filter tidak ditemukan"
    return re.findall(r'<option value="([^"]+)"', select.group(0))


def test_user_sees_four_label_filters_and_no_review_rows(roles):
    app, dataset_id, user_id, _ = roles
    client, _ = login(app, "role-user@test.local")
    response = client.get(f"/preprocessing?dataset_id={dataset_id}")
    assert response.status_code == 200
    html = response.data.decode()

    assert options_in(html) == ["semua", "sudah", "positif", "negatif", "netral"]
    # Review rows are hidden from regular users entirely.
    assert "tidak buruk" not in html
    assert "entah apa" not in html
    # Labelled rows are still visible.
    for text in ("tambang bagus", "tambang merusak", "tambang biasa"):
        assert text in html
    # Superadmin-only columns and controls stay out of the markup.
    assert "<th>Sumber</th>" not in html
    assert "<th>Skor</th>" not in html
    assert "/preprocessing/labels/manual" not in html
    assert "Jalankan Pelabelan Lexicon" not in html


def test_user_review_filter_falls_back_to_all_visible_rows(roles):
    app, dataset_id, _, _ = roles
    client, _ = login(app, "role-user@test.local")
    response = client.get(f"/preprocessing?dataset_id={dataset_id}&label=review")
    assert response.status_code == 200
    html = response.data.decode()
    # Forbidden filter is ignored rather than rejected: 3 visible rows, no review row.
    assert "3 komentar cocok" in html
    assert "entah apa" not in html


def test_user_filter_sudah_lists_labelled_rows_only(roles):
    app, dataset_id, _, _ = roles
    client, _ = login(app, "role-user@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset_id}&label=sudah").data.decode()
    assert "3 komentar cocok" in html


def test_superadmin_sees_all_filters_and_review_rows(roles):
    app, dataset_id, _, admin_id = roles
    with app.app_context():
        # Give the admin their own dataset copy so ownership checks pass.
        admin_dataset = Dataset(user_id=admin_id, original_filename="role-admin.csv",
                                stored_filename="role-admin-private.csv", file_path="private",
                                row_count=5, comment_column="isi", status="validated")
        db.session.add(admin_dataset)
        db.session.flush()
        source = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id)).scalars().all()
        for comment in source:
            db.session.add(Comment(dataset_id=admin_dataset.id, row_number=comment.row_number,
                                   comment_text=comment.comment_text,
                                   sentiment_label=comment.sentiment_label,
                                   label_source=comment.label_source,
                                   review_status=comment.review_status, lexicon_score=1))
        db.session.commit()
        admin_dataset_id = admin_dataset.id

    client, _ = login(app, "role-admin@test.local")
    response = client.get(f"/preprocessing?dataset_id={admin_dataset_id}")
    assert response.status_code == 200
    html = response.data.decode()

    assert options_in(html) == ["semua", "sudah", "positif", "negatif", "netral", "review", "manual", "lexicon"]
    assert "tidak buruk" in html
    assert "<th>Sumber</th>" in html
    assert "<th>Skor</th>" in html
    assert "Jalankan Ulang Pelabelan Otomatis" in html


def test_imported_rows_without_review_status_stay_visible_to_user(roles):
    app, dataset_id, _, _ = roles
    with app.app_context():
        db.session.add(Comment(dataset_id=dataset_id, row_number=99, comment_text="komentar impor manual",
                               sentiment_label="Positif", label_source="manual", manual_label="Positif",
                               review_status=None))
        db.session.commit()
    client, _ = login(app, "role-user@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset_id}").data.decode()
    assert "komentar impor manual" in html
    assert "4 komentar cocok" in html
