from functools import wraps
from flask import Blueprint, abort, redirect, request, url_for, render_template
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import User, Dataset, Comment
from sqlalchemy import func

bp = Blueprint("auth", __name__)


def superadmin_required(fn):
    @wraps(fn)
    @login_required
    def inner(*args, **kwargs):
        if current_user.role != "superadmin":
            abort(403)
        return fn(*args, **kwargs)
    return inner


@bp.post("/register")
def register():
    name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not name or len(name) > 150 or len(email) > 255 or "@" not in email or len(password) < 12:
        return "Data registrasi tidak valid", 400
    user = User(full_name=name, email=email, role="user")
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return "Email telah terdaftar", 409
    return redirect(url_for("auth.login_hint"))


@bp.get("/register")
def register_form():
    return render_template("auth/register.html")


@bp.get("/login")
def login_hint():
    return render_template("auth/login.html")


@bp.post("/login")
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    if not user or not user.check_password(password):
        return "Email atau password salah", 401
    login_user(user)
    return redirect(url_for("auth.dashboard"))


@bp.get("/dashboard")
@login_required
def dashboard():
    dataset = db.session.execute(db.select(Dataset).filter_by(user_id=current_user.id).order_by(Dataset.id.desc())).scalars().first()
    count = db.session.scalar(db.select(func.count(Comment.id)).filter_by(dataset_id=dataset.id)) if dataset else None
    labels = {}
    if dataset:
        labels = dict(db.session.execute(db.select(Comment.sentiment_label, func.count(Comment.id)).filter(Comment.dataset_id == dataset.id, Comment.sentiment_label.is_not(None)).group_by(Comment.sentiment_label)).all())
    return render_template("dashboard/index.html", dataset=dataset, count=count, labels=labels)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_hint"))


@bp.get("/admin/health")
@superadmin_required
def admin_health():
    return "Admin tersedia"
