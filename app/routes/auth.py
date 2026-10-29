from functools import wraps
from flask import Blueprint, abort, redirect, request, url_for, render_template
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import User
from app.services.dashboard_service import dashboard_context

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
    field_errors = {}
    if not name:
        field_errors["full_name"] = "Nama lengkap wajib diisi."
    elif len(name) > 150:
        field_errors["full_name"] = "Nama lengkap maksimal 150 karakter."
    if not email or "@" not in email or len(email) > 255:
        field_errors["email"] = "Masukkan alamat email yang valid."
    if len(password) < 12:
        field_errors["password"] = "Password minimal 12 karakter."
    if field_errors:
        return render_template(
            "auth/register.html",
            field_errors=field_errors,
            form_values={"full_name": name, "email": email},
        ), 400
    user = User(full_name=name, email=email, role="user")
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return render_template(
            "auth/register.html",
            field_errors={"email": "Email telah terdaftar."},
            form_values={"full_name": name, "email": email},
        ), 409
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
    field_errors = {}
    if not email or "@" not in email or len(email) > 255:
        field_errors["email"] = "Masukkan alamat email yang valid."
    if not password:
        field_errors["password"] = "Password wajib diisi."
    if field_errors:
        return render_template(
            "auth/login.html",
            field_errors=field_errors,
            form_values={"email": email},
        ), 400
    user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    if not user or not user.check_password(password):
        return render_template(
            "auth/login.html",
            field_errors={"password": "Email atau password salah."},
            form_values={"email": email},
        ), 401
    login_user(user)
    return redirect(url_for("auth.dashboard", upload=1))


@bp.get("/dashboard")
@login_required
def dashboard():
    context = dashboard_context(current_user.id)
    context['upload_modal_open'] = request.args.get('upload') == '1'
    return render_template("dashboard/index.html", **context)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_hint"))


@bp.get("/admin/health")
@superadmin_required
def admin_health():
    return "Admin tersedia"
