"""Authenticated CSV import into private storage and MySQL."""
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Dataset, Comment
from app.services.dataset_service import DatasetError, parse_csv

bp = Blueprint("datasets", __name__)


@bp.route("/datasets/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "GET":
        return render_template("datasets/upload.html")
    file = request.files.get("file")
    if not file or not file.filename or not file.filename.lower().endswith(".csv"):
        return render_template("datasets/upload.html", error="Pilih berkas CSV valid"), 400
    original = secure_filename(file.filename)
    if not original:
        return render_template("datasets/upload.html", error="Nama berkas tidak valid"), 400
    label_column = request.form.get("label_column") or None
    if label_column and current_user.role != "superadmin":
        return render_template("datasets/upload.html", error="Kolom label manual hanya boleh diimpor Superadmin"), 403
    try:
        rows, summary = parse_csv(file.stream, request.form.get("comment_column", ""), label_column)
    except DatasetError as exc:
        return render_template("datasets/upload.html", error=str(exc)), 400
    folder = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}.csv"
    path = folder / stored
    file.stream.seek(0)
    path.write_bytes(file.stream.read())
    dataset = Dataset(user_id=current_user.id, original_filename=original, stored_filename=stored,
                      file_path=str(path), row_count=summary["accepted"],
                      comment_column=request.form["comment_column"], label_column=request.form.get("label_column") or None,
                      dataset_type="train", status="validated")
    db.session.add(dataset)
    db.session.flush()
    for number, text, label in rows:
        db.session.add(Comment(dataset_id=dataset.id, row_number=number, comment_text=text,
                               manual_label=label, sentiment_label=label, label_source="manual" if label else None,
                               labeled_by=current_user.id if label else None, labeled_at=datetime.now(timezone.utc) if label else None))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        path.unlink(missing_ok=True)
        current_app.logger.exception("Dataset import failed")
        return render_template("datasets/upload.html", error="Import gagal; periksa database"), 500
    return render_template("datasets/upload.html", summary=summary, filename=original)
