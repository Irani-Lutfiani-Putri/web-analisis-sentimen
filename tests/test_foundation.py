import pytest

from app import create_app


def test_missing_secret_rejected(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://user:pass@localhost:3306/freeport")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app()


def test_missing_database_url_rejected(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_app()


def test_malformed_database_url_rejected_without_leaking_value(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "not-a-url-with-private-password")
    with pytest.raises(ValueError, match="DATABASE_URL") as exc:
        create_app()
    assert "private-password" not in str(exc.value)


def test_non_mysql_database_rejected(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    with pytest.raises(ValueError, match="MySQL"):
        create_app()


def test_health_reports_database_unavailable_without_secrets(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://user:pass@127.0.0.1:1/freeport")
    app = create_app()
    response = app.test_client().get("/health/db")
    assert response.status_code == 503
    assert response.json == {"status": "unavailable"}
    assert b"pass" not in response.data
