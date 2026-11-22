import os
import subprocess
import sys
from pathlib import Path

import pymysql
import pytest
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
DATABASE = "sentiment_freeport_migration_test"


def run_flask(database_url, *args):
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": database_url,
        "SECRET_KEY": "migration-test-secret",
        "SESSION_COOKIE_SECURE": "false",
    })
    result = subprocess.run(
        [sys.executable, "-m", "flask", "--app", "run.py", "db", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.fixture
def migration_database():
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    parsed = make_url(test_url)
    server = pymysql.connect(
        host=parsed.host,
        port=parsed.port or 3306,
        user=parsed.username,
        password=parsed.password or "",
        autocommit=True,
    )
    with server.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS `{DATABASE}`")
        cursor.execute(
            f"CREATE DATABASE `{DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    server.commit()
    database_url = parsed.set(database=DATABASE).render_as_string(hide_password=False)
    try:
        yield database_url, server
    finally:
        with server.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{DATABASE}`")
        server.commit()
        server.close()


def test_role_column_drops_and_users_survive(migration_database):
    database_url, server = migration_database
    run_flask(database_url, "upgrade", "7a0bc825f371")

    server.select_db(DATABASE)
    with server.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, NOW(), NOW()), (%s, %s, %s, %s, NOW(), NOW())",
            (
                "Lama User", "lama-user@test.local", "x", "user",
                "Lama Admin", "lama-admin@test.local", "x", "superadmin",
            ),
        )
    server.commit()

    run_flask(database_url, "upgrade", "head")
    with server.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM users")
        columns = {row[0] for row in cursor.fetchall()}
        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]
    assert "role" not in columns
    assert users == 2

    run_flask(database_url, "downgrade", "7a0bc825f371")
    with server.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM users")
        columns = {row[0] for row in cursor.fetchall()}
        cursor.execute("SELECT role FROM users ORDER BY id")
        roles = [row[0] for row in cursor.fetchall()]
    assert "role" in columns
    assert roles == ["user", "user"]
