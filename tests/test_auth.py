import os
import pytest
from sqlalchemy import text
from app import create_app
from app.extensions import db


@pytest.fixture
def client(monkeypatch):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "test-only-secret")
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_register_ignores_submitted_admin_role_and_hashes_password(client):
    from app.models import User
    response = client.post("/register", data={"full_name":"Peneliti", "email":"peneliti@example.test", "password":"rahasia-kuat-123", "role":"superadmin"})
    assert response.status_code == 302
    with client.application.app_context():
        user = db.session.execute(db.select(User).filter_by(email="peneliti@example.test")).scalar_one()
        assert user.role == "user"
        assert user.password_hash != "rahasia-kuat-123"
        assert user.check_password("rahasia-kuat-123")


def test_login_and_logout_session(client):
    client.post("/register", data={"full_name":"Peneliti", "email":"peneliti@example.test", "password":"rahasia-kuat-123"})
    assert client.post("/login", data={"email":"peneliti@example.test", "password":"wrong"}).status_code == 401
    assert client.post("/login", data={"email":"peneliti@example.test", "password":"rahasia-kuat-123"}).status_code == 302
    assert client.get("/dashboard").status_code == 200
    assert client.post("/logout").status_code == 302
    assert client.get("/dashboard").status_code == 302


def test_user_cannot_access_admin_endpoint_directly(client):
    client.post("/register", data={"full_name":"Peneliti", "email":"peneliti@example.test", "password":"rahasia-kuat-123"})
    client.post("/login", data={"email":"peneliti@example.test", "password":"rahasia-kuat-123"})
    assert client.get("/admin/health").status_code == 403


def test_csrf_rejects_posts_without_token(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post("/register", data={"full_name":"Peneliti", "email":"x@example.test", "password":"rahasia-kuat-123"})
    assert response.status_code == 400


def test_register_with_valid_csrf_token(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        web = app.test_client()
        from itsdangerous import URLSafeTimedSerializer
        with web.session_transaction() as sess:
            sess["csrf_token"] = "test-csrf-nonce"
        token = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token").dumps("test-csrf-nonce")
        response = web.post("/register", data={"full_name":"Peneliti", "email":"csrf@example.test", "password":"rahasia-kuat-123", "csrf_token":token})
        assert response.status_code == 302
        db.session.remove()
        db.drop_all()


def test_superadmin_creation_requires_explicit_cli_credentials(client):
    from app.models import User
    runner = client.application.test_cli_runner()
    result = runner.invoke(args=["create-superadmin", "--name", "Pengelola", "--email", "admin@example.test"], env={"SUPERADMIN_INITIAL_PASSWORD": "rahasia-superadmin-123"})
    assert result.exit_code == 0
    with client.application.app_context():
        admin = db.session.execute(db.select(User).filter_by(email="admin@example.test")).scalar_one()
        assert admin.role == "superadmin"
        assert admin.check_password("rahasia-superadmin-123")
    assert "rahasia-superadmin-123" not in result.output


def test_duplicate_registration_rejected(client):
    payload={"full_name":"Peneliti", "email":"peneliti@example.test", "password":"rahasia-kuat-123"}
    assert client.post("/register", data=payload).status_code == 302
    assert client.post("/register", data=payload).status_code == 409
