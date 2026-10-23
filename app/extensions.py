from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

migrate = Migrate()


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return db.session.get(User, int(user_id)) if user_id.isdecimal() else None


@login_manager.unauthorized_handler
def unauthorized():
    from flask import redirect, url_for
    return redirect(url_for("auth.login_hint"))
