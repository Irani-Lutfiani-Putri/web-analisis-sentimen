"""Staged split, TF-IDF, SVM training, and evaluation for the signed-in owner."""
from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db, limiter
from app.models import Dataset
from app.services.training_service import (
    CLASSES, RATIOS, TrainingError, active_run, create_split,
    dataset_eligibility, run_evaluation, run_tfidf, run_training,
)

bp = Blueprint('classification', __name__)


def _index_context(**extra):
    datasets = db.session.execute(
        db.select(Dataset).filter_by(user_id=current_user.id, status='processed').order_by(Dataset.id.desc())
    ).scalars().all()
    selected_dataset = None
    if datasets:
        requested_id = extra.get('selected_dataset_id') or request.args.get('dataset_id', type=int)
        selected_dataset = next((dataset for dataset in datasets if dataset.id == requested_id), datasets[0])
    run = active_run(selected_dataset.id, current_user.id) if selected_dataset else None
    eligibility = dataset_eligibility(selected_dataset.id) if selected_dataset else None
    split_done = bool(run and run.split_at)
    tfidf_done = bool(run and run.tfidf_at)
    trained_done = bool(run and run.trained_at)
    evaluated_done = bool(run and run.evaluated_at)
    context = {
        'datasets': datasets,
        'selected_dataset': selected_dataset,
        'active_run': run,
        'eligibility': eligibility,
        'classes': CLASSES,
        'result_classes': run.split_config.get('classes', CLASSES) if run and run.split_config else CLASSES,
        'ratios': list(RATIOS.keys()),
        'selected_ratio': run.split_ratio if run else '80:20',
        'split_done': split_done,
        'tfidf_done': tfidf_done,
        'trained_done': trained_done,
        'evaluated_done': evaluated_done,
        'can_split': bool(eligibility and eligibility['ready']),
        'tfidf_ready': split_done and not tfidf_done,
        'train_ready': tfidf_done and not trained_done,
        'eval_ready': trained_done and not evaluated_done,
    }
    context.update(extra)
    return context


def _stage_dataset(dataset_id):
    dataset = db.session.get(Dataset, dataset_id) if dataset_id else None
    if not dataset or dataset.user_id != current_user.id or dataset.status != 'processed':
        abort(404)
    return dataset


def _missing_dataset():
    return render_template(
        'classification/index.html',
        **_index_context(field_errors={'dataset_id': 'Dataset hasil preprocessing tidak tersedia.'}),
    ), 400


def _stage_error(dataset, message):
    return render_template(
        'classification/index.html',
        **_index_context(selected_dataset_id=dataset.id, error=message),
    ), 400


@bp.get('/classification')
@login_required
def index():
    return render_template('classification/index.html', **_index_context())


@bp.post('/classification/split')
@limiter.limit("10 per minute")
@login_required
def split_data():
    dataset_id = request.form.get('dataset_id', type=int)
    if not dataset_id:
        return _missing_dataset()
    dataset = _stage_dataset(dataset_id)
    try:
        create_split(dataset.id, current_user.id, request.form.get('split_ratio', '70:30'))
    except TrainingError as exc:
        return _stage_error(dataset, str(exc))
    return redirect(url_for('classification.index', dataset_id=dataset.id))


@bp.post('/classification/tfidf')
@limiter.limit("10 per minute")
@login_required
def tfidf():
    dataset_id = request.form.get('dataset_id', type=int)
    if not dataset_id:
        return _missing_dataset()
    dataset = _stage_dataset(dataset_id)
    run = active_run(dataset.id, current_user.id)
    if not run:
        return _stage_error(dataset, 'Split Data belum dijalankan.')
    if run.tfidf_at:
        return _stage_error(dataset, 'TF-IDF sudah dijalankan untuk pipeline ini.')
    try:
        run_tfidf(run, current_app.config['MODEL_FOLDER'])
    except TrainingError as exc:
        return _stage_error(dataset, str(exc))
    return redirect(url_for('classification.index', dataset_id=dataset.id))


@bp.post('/classification/train')
@limiter.limit("10 per minute")
@login_required
def train():
    dataset_id = request.form.get('dataset_id', type=int)
    if not dataset_id:
        return _missing_dataset()
    dataset = _stage_dataset(dataset_id)
    run = active_run(dataset.id, current_user.id)
    if not run or not run.tfidf_at:
        return _stage_error(dataset, 'TF-IDF belum dijalankan.')
    if run.trained_at:
        return _stage_error(dataset, 'Training sudah dijalankan untuk pipeline ini.')
    try:
        run_training(run, current_app.config['MODEL_FOLDER'])
    except TrainingError as exc:
        return _stage_error(dataset, str(exc))
    return redirect(url_for('classification.index', dataset_id=dataset.id))


@bp.post('/classification/evaluate')
@limiter.limit("10 per minute")
@login_required
def evaluate():
    dataset_id = request.form.get('dataset_id', type=int)
    if not dataset_id:
        return _missing_dataset()
    dataset = _stage_dataset(dataset_id)
    run = active_run(dataset.id, current_user.id)
    if not run or not run.trained_at:
        return _stage_error(dataset, 'Training SVM belum dijalankan.')
    if run.evaluated_at:
        return _stage_error(dataset, 'Evaluasi sudah dijalankan untuk pipeline ini.')
    try:
        run_evaluation(run, current_app.config['MODEL_FOLDER'])
    except TrainingError as exc:
        return _stage_error(dataset, str(exc))
    return redirect(url_for('classification.index', dataset_id=dataset.id))
