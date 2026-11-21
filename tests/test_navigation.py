import os

import pytest

from app import create_app
from app.extensions import db


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
