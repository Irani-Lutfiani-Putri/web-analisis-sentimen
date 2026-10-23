"""Lexicon and privileged manual labeling endpoints."""
from pathlib import Path
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models import Comment, Dataset
from app.routes.auth import superadmin_required
from app.services.lexicon_service import INSET_VERSION, annotate_dataset, load_inset, update_manual_label
from app.services.preprocessing_service import process_dataset
from app.services import job_service

bp = Blueprint('preprocessing', __name__)

PAGE_SIZE = 25
LABEL_FILTERS = {'positif': 'Positif', 'negatif': 'Negatif', 'netral': 'Netral'}
FILTER_KEYS = {'semua', 'review', 'manual', 'lexicon', *LABEL_FILTERS}


def _format_score(value):
    if value is None:
        return None
    number = float(value)
    return f"{int(number)}" if number.is_integer() else f"{number:.2f}"


def _filtered_query(dataset_id, q, label):
    query = db.select(Comment).filter(Comment.dataset_id == dataset_id)
    if q:
        query = query.filter(Comment.comment_text.like(f"%{q}%"))
    if label == 'review':
        query = query.filter(Comment.review_status == 'review')
    elif label == 'manual':
        query = query.filter(Comment.label_source == 'manual')
    elif label == 'lexicon':
        query = query.filter(Comment.label_source == 'lexicon')
    elif label in LABEL_FILTERS:
        query = query.filter(Comment.sentiment_label == LABEL_FILTERS[label])
    return query


def owned_dataset(dataset_id):
    dataset = db.session.get(Dataset, dataset_id) if dataset_id else None
    if not dataset or dataset.user_id != current_user.id:
        abort(404)
    return dataset


@bp.get('/preprocessing')
@login_required
def index():
    datasets = db.session.execute(db.select(Dataset).filter_by(user_id=current_user.id).order_by(Dataset.id.desc()).limit(20)).scalars().all()
    requested_id = request.args.get('dataset_id', type=int)
    dataset = next((d for d in datasets if d.id == requested_id), None) or (datasets[0] if datasets else None)
    q = (request.args.get('q') or '').strip()[:100]
    label = request.args.get('label') or 'semua'
    if label not in FILTER_KEYS:
        label = 'semua'

    comments, total_filtered, page, total_pages = [], 0, 1, 1
    total_comments, label_counts, comparisons = 0, {}, []
    if dataset:
        base = _filtered_query(dataset.id, q, label)
        total_filtered = db.session.scalar(db.select(db.func.count()).select_from(base.subquery()))
        total_pages = max(1, -(-total_filtered // PAGE_SIZE))
        page = min(max(request.args.get('page', type=int) or 1, 1), total_pages)
        comments = db.session.execute(
            base.order_by(Comment.row_number).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
        ).scalars().all()
        total_comments = db.session.scalar(db.select(db.func.count(Comment.id)).filter(Comment.dataset_id == dataset.id))
        label_counts = dict(db.session.execute(
            db.select(Comment.sentiment_label, db.func.count(Comment.id))
            .filter(Comment.dataset_id == dataset.id, Comment.sentiment_label.is_not(None))
            .group_by(Comment.sentiment_label)).all())
        comparisons = [{'original': c.comment_text, 'cleaned': c.cleaned_text} for c in comments if c.cleaned_text is not None]

    safe_comments = [{'id': c.id, 'text': c.comment_text, 'label': c.sentiment_label} for c in comments]
    if current_user.role == 'superadmin':
        for item, c in zip(safe_comments, comments):
            item.update(score=_format_score(c.lexicon_score), source=c.label_source, review=c.review_status)
    return render_template('preprocessing/index.html', dataset=dataset, comments=safe_comments, comparisons=comparisons,
                           total_comments=total_comments, label_counts=label_counts, datasets=datasets,
                           q=q, label=label, page=page, total_pages=total_pages, total_filtered=total_filtered,
                           page_size=PAGE_SIZE)


@bp.post('/preprocessing/lexicon/run')
@login_required
def run_lexicon():
    dataset = owned_dataset(request.form.get('dataset_id', type=int))
    try:
        weights, collisions = load_inset(Path('storage/lexicon'))
    except (OSError, ValueError, KeyError):
        return 'Kamus lexicon tidak tersedia atau tidak valid', 503
    job_id = job_service.create_job('lexicon', dataset.id)
    dataset_id = dataset.id

    def work():
        return annotate_dataset(dataset_id, weights, INSET_VERSION, collisions,
                                progress=job_service.progress_callback(job_id))

    job_service.run_in_background(current_app._get_current_object(), job_id, work)
    return redirect(url_for('preprocessing.index', dataset_id=dataset_id, job=job_id))


@bp.post('/preprocessing/run')
@login_required
def run_preprocessing():
    dataset = owned_dataset(request.form.get('dataset_id', type=int))
    job_id = job_service.create_job('preprocessing', dataset.id)
    dataset_id = dataset.id

    def work():
        return {'comments': process_dataset(dataset_id, progress=job_service.progress_callback(job_id))}

    job_service.run_in_background(current_app._get_current_object(), job_id, work)
    return redirect(url_for('preprocessing.index', dataset_id=dataset_id, job=job_id))


@bp.get('/preprocessing/jobs/<job_id>')
@login_required
def job_status(job_id):
    job = job_service.get_job(job_id)
    if not job:
        abort(404)
    owned_dataset(job['dataset_id'])
    return jsonify({key: job.get(key) for key in ('id', 'kind', 'status', 'done', 'total', 'message')})


@bp.get('/preprocessing/labels/details')
@superadmin_required
def label_details():
    dataset = owned_dataset(request.args.get('dataset_id', type=int))
    comments = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset.id).order_by(Comment.row_number).limit(100)).scalars().all()
    return jsonify([{'id': c.id, 'label_source': c.label_source, 'lexicon_score': str(c.lexicon_score) if c.lexicon_score is not None else None,
                     'labeled_by': c.labeled_by, 'labeled_at': c.labeled_at.isoformat() if c.labeled_at else None,
                     'label_note': c.label_note} for c in comments])


@bp.post('/preprocessing/labels/manual')
@superadmin_required
def manual_label():
    comment = db.session.get(Comment, request.form.get('comment_id', type=int))
    if not comment:
        abort(404)
    owned_dataset(comment.dataset_id)
    try:
        update_manual_label(comment, request.form.get('label'), current_user.id, request.form.get('note'))
    except ValueError:
        return 'Label tidak valid', 400
    return redirect(url_for('preprocessing.index', dataset_id=comment.dataset_id,
                            q=request.form.get('q') or None,
                            label=request.form.get('label_filter') or None,
                            page=request.form.get('page') or None))
