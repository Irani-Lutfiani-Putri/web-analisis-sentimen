"""Superadmin workspace for reviewing and correcting lexicon labels.

Every write here delegates to the existing services (``update_manual_label``
and ``set_holdout``) so the research rules live in one place: a manual label
is never overwritten by the lexicon, and only a row that already carries a
manual label can become independent test data.
"""
from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Comment, Dataset
from app.routes.auth import superadmin_required
from app.services import comment_query
from app.services.holdout_service import HoldoutError, set_holdout, summary as holdout_summary
from app.services.lexicon_service import update_manual_label

bp = Blueprint('admin_datasets', __name__, url_prefix='/admin/datasets')

MAX_BULK = 200
VALID_LABELS = ('Positif', 'Negatif', 'Netral')


def _back(dataset_id, error=None, notice=None):
    """Return to the same page and filter the action came from."""
    return redirect(url_for('admin_datasets.index', dataset_id=dataset_id,
                            q=request.form.get('q') or None,
                            label=request.form.get('label_filter') or None,
                            page=request.form.get('page') or None,
                            error=error, notice=notice))


@bp.get('')
@superadmin_required
def index():
    datasets = db.session.execute(db.select(Dataset).filter_by(user_id=current_user.id)
                                  .order_by(Dataset.id.desc()).limit(50)).scalars().all()
    requested = request.args.get('dataset_id', type=int)
    dataset = next((d for d in datasets if d.id == requested), None) or (datasets[0] if datasets else None)
    q = (request.args.get('q') or '').strip()[:100]
    label = comment_query.normalize_filter(request.args.get('label') or 'semua', current_user.role)

    comments, total_filtered, page, total_pages = [], 0, 1, 1
    counts, pending, holdout = {}, 0, None
    if dataset:
        comments, total_filtered, page, total_pages = comment_query.paginate(
            dataset.id, q, label, current_user.role, request.args.get('page', type=int))
        counts = comment_query.label_counts(dataset.id)
        pending = comment_query.pending_review_count(dataset.id)
        holdout = holdout_summary(dataset.id)

    rows = []
    for comment in comments:
        rows.append({
            'id': comment.id,
            'text': comment.comment_text,
            'label': comment.sentiment_label,
            'source': comment.label_source,
            'score': comment_query.format_score(comment.lexicon_score),
            'review': comment.review_status,
            'manual': comment.manual_label,
            'holdout': comment.is_independent_holdout,
            'eligible': not comment.is_independent_holdout and comment.manual_label is not None
                        and comment.label_source == 'manual'
                        and comment.sentiment_label == comment.manual_label,
        })

    return render_template('admin_datasets/index.html',
                           datasets=datasets, dataset=dataset, comments=rows,
                           total_filtered=total_filtered, page=page, total_pages=total_pages,
                           label_counts=counts, pending_review=pending, holdout=holdout,
                           q=q, label=label,
                           filter_options=comment_query.filter_options(current_user.role),
                           error=request.args.get('error'), notice=request.args.get('notice'))


@bp.post('/label')
@superadmin_required
def save_label():
    comment = db.session.get(Comment, request.form.get('comment_id', type=int))
    if not comment:
        abort(404)
    dataset = comment_query.owned_dataset(comment.dataset_id)
    try:
        update_manual_label(comment, request.form.get('label'), current_user.id,
                            request.form.get('note') or None)
    except ValueError:
        return _back(dataset.id, error='Label tidak valid; pilih Positif, Negatif, atau Netral.')
    return _back(dataset.id, notice=f'Label komentar #{comment.id} disimpan sebagai {comment.sentiment_label}.')


@bp.post('/label/bulk')
@superadmin_required
def save_label_bulk():
    dataset = comment_query.owned_dataset(request.form.get('dataset_id', type=int))
    label = request.form.get('label')
    if label not in VALID_LABELS:
        return _back(dataset.id, error='Label tidak valid; pilih Positif, Negatif, atau Netral.')
    raw_ids = request.form.getlist('comment_ids')
    ids = []
    for value in raw_ids[:MAX_BULK]:
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    if not ids:
        return _back(dataset.id, error='Pilih minimal satu komentar untuk diberi label.')
    comments = db.session.execute(
        db.select(Comment).filter(Comment.dataset_id == dataset.id, Comment.id.in_(ids))
    ).scalars().all()
    for comment in comments:
        update_manual_label(comment, label, current_user.id, request.form.get('note') or None)
    return _back(dataset.id, notice=f'{len(comments)} komentar diberi label manual {label}.')


@bp.post('/holdout')
@superadmin_required
def toggle_holdout():
    comment = db.session.get(Comment, request.form.get('comment_id', type=int))
    if not comment:
        abort(404)
    dataset = comment_query.owned_dataset(comment.dataset_id)
    value = request.form.get('value') == '1'
    try:
        set_holdout(comment, current_user.id, value)
    except PermissionError:
        abort(403)
    except HoldoutError as exc:
        return _back(dataset.id, error=str(exc))
    state = 'ditandai' if value else 'dilepas'
    return _back(dataset.id, notice=f'Data uji independen komentar #{comment.id} {state}.')
