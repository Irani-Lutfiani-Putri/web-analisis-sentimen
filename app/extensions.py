from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask import request

migrate = Migrate()


def client_ip() -> str:
    """IP klien dari Nginx, bukan 127.0.0.1 milik proxy."""
    return (
        request.headers.get("X-Real-IP")
        or request.headers.get("CF-Connecting-IP")
        or request.remote_addr
        or "unknown"
    )


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=client_ip,
    default_limits=[],
    storage_uri="memory://",
    headers_enabled=True,
)


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return db.session.get(User, int(user_id)) if user_id.isdecimal() else None


@login_manager.unauthorized_handler
def unauthorized():
    from flask import redirect, url_for
    return redirect(url_for("auth.login_hint"))
