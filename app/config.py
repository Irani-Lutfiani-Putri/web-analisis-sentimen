"""Validated environment configuration for MySQL-backed Flask app."""
import os

from sqlalchemy.engine import make_url


def load_config():
    secret = os.environ.get("SECRET_KEY", "")
    database = os.environ.get("DATABASE_URL", "")
    if not secret:
        raise ValueError("SECRET_KEY wajib diatur di environment")
    if not database:
        raise ValueError("DATABASE_URL wajib diatur untuk MySQL")
    try:
        url = make_url(database)
    except Exception as exc:
        raise ValueError("DATABASE_URL tidak valid untuk MySQL") from exc
    if url.drivername != "mysql+pymysql" or not url.database:
        raise ValueError("DATABASE_URL harus memakai MySQL (mysql+pymysql)")
    return {
        "SECRET_KEY": secret,
        "SQLALCHEMY_DATABASE_URI": database,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
        "MAX_CONTENT_LENGTH": int(os.environ.get("MAX_CONTENT_LENGTH", "16777216")),
        "UPLOAD_FOLDER": os.environ.get("UPLOAD_FOLDER", "storage/uploads"),
        "MODEL_FOLDER": os.environ.get("MODEL_FOLDER", "storage/models"),
        "LEXICON_FOLDER": os.environ.get("LEXICON_FOLDER", "storage/lexicon"),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true",
    }
