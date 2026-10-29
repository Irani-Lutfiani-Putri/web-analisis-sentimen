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


def test_register_renders_field_specific_errors(client):
    response = client.post('/register', data={
        'full_name': '', 'email': 'invalid', 'password': 'short'
    })
    assert response.status_code == 400
    assert b'id="full_name-error"' in response.data
    assert b'id="email-error"' in response.data
    assert b'id="password-error"' in response.data
    assert b'aria-invalid="true"' in response.data


def test_duplicate_email_error_stays_on_email_field(client):
    payload = {'full_name': 'Peneliti', 'email': 'duplikat@example.test', 'password': 'rahasia-kuat-123'}
    assert client.post('/register', data=payload).status_code == 302
    response = client.post('/register', data=payload)
    assert response.status_code == 409
    assert b'id="email-error"' in response.data
    assert b'value="duplikat@example.test"' in response.data


def test_login_error_is_attached_to_password_without_account_disclosure(client):
    response = client.post('/login', data={'email': 'unknown@example.test', 'password': 'wrong'})
    assert response.status_code == 401
    assert b'id="password-error"' in response.data
    assert b'Email atau password salah' in response.data
    assert b'value="unknown@example.test"' in response.data
    assert b'value="wrong"' not in response.data


def test_login_required_fields_render_on_their_own_inputs(client):
    response = client.post('/login', data={'email': 'invalid', 'password': ''})
    assert response.status_code == 400
    assert b'id="email-error"' in response.data
    assert b'id="password-error"' in response.data
    assert response.data.count(b'aria-invalid="true"') == 2


def test_login_and_logout_session(client):
    client.post("/register", data={"full_name":"Peneliti", "email":"peneliti@example.test", "password":"rahasia-kuat-123"})
    assert client.post("/login", data={"email":"peneliti@example.test", "password":"wrong"}).status_code == 401
    login = client.post("/login", data={"email":"peneliti@example.test", "password":"rahasia-kuat-123"})
    assert login.status_code == 302
    assert login.location.endswith("/dashboard?upload=1")
    landing = client.get(login.location)
    assert landing.status_code == 200
    assert b'id="upload-dataset-dialog"' in landing.data
    assert b'data-auto-open' in landing.data
    normal_dashboard = client.get("/dashboard")
    assert normal_dashboard.status_code == 200
    assert b'data-auto-open' not in normal_dashboard.data
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
