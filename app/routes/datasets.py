"""Authenticated CSV import into private storage and MySQL."""
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Dataset, Comment
from app.services import job_service
from app.services.dashboard_service import dashboard_context
from app.services.dataset_service import DatasetError, parse_csv
from app.services.lexicon_service import INSET_VERSION, LexiconError, annotate_dataset, load_inset

bp = Blueprint("datasets", __name__)


def _dashboard_modal(*, error=None, field_errors=None, form_values=None, summary=None,
                     filename=None, lexicon_warning=None, status=200):
    context = dashboard_context(current_user.id)
    context.update(
        upload_modal_open=True,
        upload_error=error,
        upload_field_errors=field_errors or {},
        upload_form_values=form_values or {},
        upload_summary=summary,
        upload_filename=filename,
        lexicon_warning=lexicon_warning,
    )
    return render_template("dashboard/index.html", **context), status


def _lexicon_ready(folder):
    """The lexicon is optional for import but required for auto-labeling."""
    return all((folder / name).is_file() for name in ("positive.tsv", "negative.tsv"))


def _start_auto_lexicon(app, dataset_id):
    """Label the freshly imported dataset in the background, exactly once."""
    job_id = job_service.create_job("lexicon", dataset_id)

    def work():
        folder = Path(app.config["LEXICON_FOLDER"]).resolve()
        weights, collisions = load_inset(folder)
        return annotate_dataset(dataset_id, weights, INSET_VERSION, collisions,
                                progress=job_service.progress_callback(job_id))

    job_service.run_in_background(app, job_id, work)
    return job_id


@bp.route("/datasets/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "GET":
        return _dashboard_modal()
    file = request.files.get("file")
    values = {
        "comment_column": request.form.get("comment_column", ""),
        "label_column": request.form.get("label_column", ""),
    }
    if not file or not file.filename or not file.filename.lower().endswith(".csv"):
        return _dashboard_modal(
            field_errors={"upload_file": "Pilih berkas CSV valid."},
            form_values=values,
            status=400,
        )
    original = secure_filename(file.filename)
    if not original:
        return _dashboard_modal(
            field_errors={"upload_file": "Nama berkas tidak valid."},
            form_values=values,
            status=400,
        )
    label_column = request.form.get("label_column") or None
    if label_column and current_user.role != "superadmin":
        return _dashboard_modal(
            field_errors={"upload_label_column": "Kolom label manual hanya boleh diimpor Superadmin."},
            form_values=values,
            status=403,
        )
    try:
        rows, summary = parse_csv(file.stream, request.form.get("comment_column", ""), label_column)
    except DatasetError as exc:
        field = {
            "file": "upload_file",
            "comment_column": "upload_comment_column",
            "label_column": "upload_label_column",
        }.get(exc.field or "file", "upload_file")
        return _dashboard_modal(
            field_errors={field: str(exc)},
            form_values=values,
            status=400,
        )
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
        return _dashboard_modal(error="Import gagal; periksa database", status=500)

    folder = Path(current_app.config["LEXICON_FOLDER"]).resolve()
    if _lexicon_ready(folder):
        try:
            job_id = _start_auto_lexicon(current_app._get_current_object(), dataset.id)
        except (OSError, ValueError, KeyError, LexiconError):
            current_app.logger.exception("Auto lexicon could not start")
            return _dashboard_modal(
                summary=summary,
                filename=original,
                lexicon_warning="Dataset tersimpan, tetapi pelabelan lexicon otomatis gagal dimulai. "
                                "Superadmin dapat menjalankannya dari halaman Preprocessing.",
            )
        return redirect(url_for("preprocessing.index", dataset_id=dataset.id, job=job_id))

    return _dashboard_modal(
        summary=summary,
        filename=original,
        lexicon_warning="Dataset tersimpan tanpa label lexicon karena kamus belum tersedia. "
                        "Letakkan positive.tsv dan negative.tsv di folder lexicon, "
                        "lalu Superadmin menjalankan pelabelan dari halaman Preprocessing.",
    )
