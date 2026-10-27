"""Create the Laragon MySQL databases for this project and run migrations.

Usage (from the project root, inside the venv):
    .venv/Scripts/python.exe python_instruct/setup_laragon_db.py

Reads DB credentials from .env (DB_HOST/DB_PORT/DB_NAME/DB_TEST_NAME/DB_USER/
DB_PASS) and never prints the password. Safe to re-run: databases are created
only when missing and `flask db upgrade` is idempotent.
"""
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env_file = ROOT / ".env"
    if not env_file.is_file():
        sys.exit("File .env belum ada. Salin .env.example menjadi .env lalu isi kredensialnya.")
    values = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def main():
    env = load_env()
    host = env.get("DB_HOST", "127.0.0.1")
    port = env.get("DB_PORT", "3306")
    user = env.get("DB_USER", "root")
    password = env.get("DB_PASS", "")
    databases = [env.get("DB_NAME", "sentiment_freeport"), env.get("DB_TEST_NAME", "sentiment_freeport_test")]

    try:
        import pymysql
    except ImportError:
        sys.exit("PyMySQL belum terpasang. Jalankan: uv pip install --python .venv/Scripts/python.exe -r requirements.txt")

    connection = pymysql.connect(host=host, port=int(port), user=user, password=password, charset="utf8mb4")
    try:
        with connection.cursor() as cursor:
            for name in databases:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                print(f"database siap: {name}")
            cursor.execute("SELECT VERSION()")
            print(f"MySQL {cursor.fetchone()[0]} di {host}:{port} (user {user})")
    finally:
        connection.close()

    database_url = (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/"
        f"{databases[0]}?charset=utf8mb4"
    )
    test_url = (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/"
        f"{databases[1]}?charset=utf8mb4"
    )
    print("\nTambahkan baris berikut ke .env bila belum ada:")
    print(f"DATABASE_URL={database_url}")
    print(f"TEST_DATABASE_URL={test_url}")

    child_env = {**os.environ, "DATABASE_URL": database_url}
    for key in ("SECRET_KEY",):
        if env.get(key):
            child_env[key] = env[key]
    python = str(ROOT / ".venv" / "Scripts" / "python.exe")
    if not Path(python).is_file():
        python = sys.executable
    print("\nMenjalankan migration…")
    result = subprocess.run([python, "-m", "flask", "--app", "run.py", "db", "upgrade"],
                            cwd=str(ROOT), env=child_env)
    if result.returncode != 0:
        sys.exit("Migration gagal. Periksa DATABASE_URL dan SECRET_KEY di .env.")
    print("Migration selesai.")


if __name__ == "__main__":
    main()
