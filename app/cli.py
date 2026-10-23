"""Explicit administrator bootstrap, never exposed over HTTP."""
import os
import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import User


@click.command("create-superadmin")
@click.option("--name", required=True)
@click.option("--email", required=True)
@with_appcontext
def create_superadmin(name, email):
    password = os.environ.get("SUPERADMIN_INITIAL_PASSWORD", "")
    if len(password) < 12 or not name.strip() or "@" not in email:
        raise click.ClickException("Nama, email, atau SUPERADMIN_INITIAL_PASSWORD tidak valid")
    user = User(full_name=name.strip(), email=email.strip().lower(), role="superadmin")
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise click.ClickException("Email sudah terdaftar") from None
    click.echo("Akun Superadmin dibuat")
