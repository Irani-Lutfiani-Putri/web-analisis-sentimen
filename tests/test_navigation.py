import os

import pytest

from app import create_app
from app.extensions import db
from app.models import Dataset, User


@pytest.fixture
def client(monkeypatch):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
    yield app.test_client()
    with app.app_context():
        db.session.remove()
        db.drop_all()


def register_and_login(client, email="nav@test.local"):
    assert client.post("/register", data={
        "full_name": "Peneliti", "email": email, "password": "rahasia-kuat-123",
    }).status_code == 302
    assert client.post("/login", data={
        "email": email, "password": "rahasia-kuat-123",
    }).status_code == 302


def test_sidebar_has_no_role_or_labels_menu(client):
    register_and_login(client)
    html = client.get("/dashboard").data.decode()
    assert "Kelola Dataset" not in html
    assert "Super Admin" not in html
    assert ">Admin<" not in html
    assert ">User<" not in html
    assert ">Review dan Label<" not in html


def test_register_redirects_to_login(client):
    response = client.post("/register", data={
        "full_name": "Peneliti", "email": "login@test.local", "password": "rahasia-kuat-123",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_classification_guidance_points_to_labels(client):
    register_and_login(client)
    with client.application.app_context():
        user = db.session.execute(db.select(User).filter_by(email="nav@test.local")).scalar_one()
        db.session.add(Dataset(
            user_id=user.id,
            original_filename="guidance.csv",
            stored_filename="guidance-private.csv",
            file_path="private",
            row_count=1,
            comment_column="isi",
            status="processed",
        ))
        db.session.commit()
        db.session.remove()
    response = client.get("/classification")
    assert response.status_code == 200
    html = response.data.decode()
    assert "Review dan Label" in html
    assert "halaman Preprocessing" not in html
    assert "Dashboard Klasifikasi Sentimen" in html
    assert "TF-IDF" in html
    assert "Split Data" in html
    assert "Training SVM" in html
    assert "Proses TF-IDF" in html
    assert "Split Dataset" in html
    assert "Training Model" in html
    assert "Evaluasi Model" in html
