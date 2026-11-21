"""Lexicon rerun, text preprocessing, and comment listing."""
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Comment, Dataset
from app.services.comment_query import (
    PAGE_SIZE, PREPROCESS_FILTER_KEYS, filter_options, label_counts, normalize_filter,
    owned_dataset, paginate, pending_review_count,
)
from app.services.lexicon_service import INSET_VERSION, LexiconError, annotate_dataset, load_inset
from app.services.preprocessing_service import process_dataset
from app.services import job_service

bp = Blueprint('preprocessing', __name__)


def _index_context(dataset, q, label, page_arg, **extra):
    """Everything the preprocessing template needs; shared by index and error paths."""
    comments, total_filtered, page, total_pages = [], 0, 1, 1
    total_comments, counts, comparisons, pending = 0, {}, [], 0
    datasets = db.session.execute(db.select(Dataset).filter_by(user_id=current_user.id)
                                  .order_by(Dataset.id.desc()).limit(20)).scalars().all()
    if dataset:
        comments, total_filtered, page, total_pages = paginate(
            dataset.id, q, label, page_arg, include_review=False
        )
        total_comments = db.session.scalar(
            db.select(db.func.count(Comment.id)).filter(Comment.dataset_id == dataset.id)
        )
        counts = label_counts(dataset.id)
        pending = pending_review_count(dataset.id)
        comparisons = [
            {
                'original': c.comment_text,
                'cleaned': c.cleaned_text,
                'label': c.sentiment_label or 'Perlu review',
            }
            for c in comments if c.cleaned_text is not None
        ]

    safe_comments = [
        {'id': c.id, 'text': c.comment_text, 'label': c.sentiment_label}
        for c in comments
    ]
    context = {
        'dataset': dataset, 'comments': safe_comments, 'comparisons': comparisons,
        'total_comments': total_comments, 'label_counts': counts, 'datasets': datasets,
        'q': q, 'label': label, 'page': page, 'total_pages': total_pages,
        'total_filtered': total_filtered, 'page_size': PAGE_SIZE,
        'filter_options': filter_options(PREPROCESS_FILTER_KEYS),
        'pending_review': pending,
        'labels_url': f'/labels?dataset_id={dataset.id}' if dataset else None,
    }
    context.update(extra)
    return context


@bp.get('/preprocessing')
@login_required
def index():
    datasets = db.session.execute(db.select(Dataset).filter_by(user_id=current_user.id)
                                  .order_by(Dataset.id.desc()).limit(20)).scalars().all()
    requested_id = request.args.get('dataset_id', type=int)
    dataset = next((d for d in datasets if d.id == requested_id), None) or (datasets[0] if datasets else None)
    q = (request.args.get('q') or '').strip()[:100]
    label = normalize_filter(request.args.get('label') or 'semua', PREPROCESS_FILTER_KEYS)
    context = _index_context(dataset, q, label, request.args.get('page', type=int))
    context['job_id'] = request.args.get('job')
    return render_template('preprocessing/index.html', **context)


@bp.post('/preprocessing/lexicon/run')
@login_required
def run_lexicon():
    dataset = owned_dataset(request.form.get('dataset_id', type=int))
    folder = Path(current_app.config['LEXICON_FOLDER']).resolve()
    try:
        weights, collisions = load_inset(folder)
    except LexiconError as exc:
        current_app.logger.warning('Lexicon unavailable: %s', exc)
        return render_template('preprocessing/index.html',
                               lexicon_error=str(exc), **_index_context(dataset, '', 'semua', 1)), 503
    except (OSError, ValueError, KeyError) as exc:
        current_app.logger.warning('Lexicon unreadable: %s', exc)
        return render_template('preprocessing/index.html',
                               lexicon_error='Kamus sentimen tidak dapat dibaca',
                               **_index_context(dataset, '', 'semua', 1)), 503
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
