import os
import pytest
from itsdangerous import URLSafeTimedSerializer
from app import create_app
from app.extensions import db


@pytest.fixture
def app_client(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def token_for(client):
    with client.session_transaction() as session:
        session["csrf_token"] = "page-test-nonce"
    return URLSafeTimedSerializer(client.application.secret_key, salt="wtf-csrf-token").dumps("page-test-nonce")


def test_public_pages_render_with_real_links(app_client):
    for path in ("/", "/login", "/register"):
        response = app_client.get(path)
        assert response.status_code == 200
        assert b"Pertambangan PT Freeport Indonesia" in response.data or b"PT Freeport Indonesia" in response.data
    assert b'href="/login"' in app_client.get("/").data


def test_private_pages_redirect_anonymous(app_client):
    for path in ("/dashboard", "/datasets/upload", "/preprocessing", "/classification", "/testing"):
        response = app_client.get(path)
        assert response.status_code == 302
        assert response.location.endswith("/login")


def test_private_pages_render_after_login_and_no_fake_numbers(app_client):
    csrf = token_for(app_client)
    assert app_client.post("/register", data={"full_name":"Peneliti", "email":"pages@example.test", "password":"rahasia-kuat-123", "csrf_token":csrf}).status_code == 302
    assert app_client.post("/login", data={"email":"pages@example.test", "password":"rahasia-kuat-123", "csrf_token":csrf}).status_code == 302
    for path in ("/dashboard", "/datasets/upload", "/preprocessing", "/classification", "/testing"):
        response = app_client.get(path)
        assert response.status_code == 200
        assert b"Logout" in response.data
        assert b'href="/preprocessing"' in response.data
        assert b'href="/classification"' in response.data
        assert b'href="/testing"' in response.data
        assert b'href="/lexicon"' not in response.data
    assert b"Belum ada dataset aktif" in app_client.get("/dashboard").data
    assert app_client.post("/logout", data={"csrf_token":csrf}).status_code == 302
    assert app_client.get("/dashboard").status_code == 302
