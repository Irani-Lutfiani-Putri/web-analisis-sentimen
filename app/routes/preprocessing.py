"""Lexicon and privileged manual labeling endpoints."""
from pathlib import Path
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models import Comment, Dataset
from app.routes.auth import superadmin_required
from app.services.comment_query import (
    PAGE_SIZE, filter_options, format_score, label_counts, normalize_filter, owned_dataset,
    paginate, pending_review_count,
)
from app.services.holdout_service import HoldoutError, set_holdout, summary as holdout_summary
from app.services.lexicon_service import (
    INSET_VERSION, LexiconError, annotate_dataset, load_inset, update_manual_label,
)
from app.services.preprocessing_service import process_dataset
from app.services import job_service

bp = Blueprint('preprocessing', __name__)


def _index_context(dataset, q, label, page_arg):
    """Everything the preprocessing template needs; shared by index and error paths."""
    comments, total_filtered, page, total_pages = [], 0, 1, 1
    total_comments, counts, comparisons, pending = 0, {}, [], 0
    role = current_user.role
    datasets = db.session.execute(db.select(Dataset).filter_by(user_id=current_user.id)
                                  .order_by(Dataset.id.desc()).limit(20)).scalars().all()
    if dataset:
        comments, total_filtered, page, total_pages = paginate(dataset.id, q, label, role, page_arg)
        total_comments = db.session.scalar(db.select(db.func.count(Comment.id)).filter(Comment.dataset_id == dataset.id))
        counts = label_counts(dataset.id)
        pending = pending_review_count(dataset.id)
        comparisons = [{'original': c.comment_text, 'cleaned': c.cleaned_text} for c in comments if c.cleaned_text is not None]

    safe_comments = [{'id': c.id, 'text': c.comment_text, 'label': c.sentiment_label} for c in comments]
    if role == 'superadmin':
        for item, c in zip(safe_comments, comments):
            item.update(score=format_score(c.lexicon_score), source=c.label_source, review=c.review_status,
                        manual=c.manual_label, holdout=c.is_independent_holdout,
                        eligible=not c.is_independent_holdout and c.manual_label is not None
                        and c.label_source == 'manual' and c.sentiment_label == c.manual_label)
    return {
        'dataset': dataset, 'comments': safe_comments, 'comparisons': comparisons,
        'total_comments': total_comments, 'label_counts': counts, 'datasets': datasets,
        'q': q, 'label': label, 'page': page, 'total_pages': total_pages,
        'total_filtered': total_filtered, 'page_size': PAGE_SIZE,
        'holdout': holdout_summary(dataset.id) if dataset else None,
        'filter_options': filter_options(role), 'is_superadmin': role == 'superadmin',
        'pending_review': pending,
    }


@bp.get('/preprocessing')
@login_required
def index():
    datasets = db.session.execute(db.select(Dataset).filter_by(user_id=current_user.id).order_by(Dataset.id.desc()).limit(20)).scalars().all()
    requested_id = request.args.get('dataset_id', type=int)
    dataset = next((d for d in datasets if d.id == requested_id), None) or (datasets[0] if datasets else None)
    q = (request.args.get('q') or '').strip()[:100]
    label = normalize_filter(request.args.get('label') or 'semua', current_user.role)
    context = _index_context(dataset, q, label, request.args.get('page', type=int))
    context['holdout_error'] = request.args.get('holdout_error')
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
                               lexicon_error='Kamus lexicon tidak dapat dibaca',
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


@bp.get('/preprocessing/labels/details')
@superadmin_required
def label_details():
    dataset = owned_dataset(request.args.get('dataset_id', type=int))
    comments = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset.id).order_by(Comment.row_number).limit(100)).scalars().all()
    return jsonify([{'id': c.id, 'label_source': c.label_source, 'lexicon_score': str(c.lexicon_score) if c.lexicon_score is not None else None,
                     'labeled_by': c.labeled_by, 'labeled_at': c.labeled_at.isoformat() if c.labeled_at else None,
                     'label_note': c.label_note} for c in comments])


@bp.post('/preprocessing/labels/holdout')
@superadmin_required
def set_holdout_flag():
    """Flag/unflag an independent manual test row (Superadmin only)."""
    comment = db.session.get(Comment, request.form.get('comment_id', type=int))
    if not comment:
        abort(404)
    dataset = owned_dataset(comment.dataset_id)
    value = request.form.get('value') == '1'
    try:
        set_holdout(comment, current_user.id, value)
    except PermissionError:
        abort(403)
    except HoldoutError as exc:
        return redirect(url_for('preprocessing.index', dataset_id=dataset.id,
                                q=request.form.get('q') or None,
                                label=request.form.get('label_filter') or None,
                                page=request.form.get('page') or None,
                                holdout_error=str(exc)))
    return redirect(url_for('preprocessing.index', dataset_id=dataset.id,
                            q=request.form.get('q') or None,
                            label=request.form.get('label_filter') or None,
                            page=request.form.get('page') or None))


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
