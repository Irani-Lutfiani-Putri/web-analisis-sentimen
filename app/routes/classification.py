"""Training and evaluation tied to the signed-in dataset owner."""
from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models import Dataset, ModelRun
from app.services.training_service import TrainingError, train_dataset
from app.services.holdout_service import summary as holdout_summary

bp = Blueprint('classification', __name__)


@bp.get('/classification')
@login_required
def index():
    datasets = db.session.execute(db.select(Dataset).filter_by(user_id=current_user.id, status='processed').order_by(Dataset.id.desc())).scalars().all()
    runs = db.session.execute(db.select(ModelRun).filter_by(user_id=current_user.id, status='completed').order_by(ModelRun.id.desc()).limit(10)).scalars().all()
    holdouts = {dataset.id: holdout_summary(dataset.id) for dataset in datasets}
    return render_template('classification/index.html', datasets=datasets, runs=runs, holdouts=holdouts)


@bp.post('/classification/train')
@login_required
def train():
    dataset_id = request.form.get('dataset_id', type=int)
    if not dataset_id:
        return 'Pilih dataset hasil preprocessing', 400
    try:
        train_dataset(dataset_id, current_user.id, current_app.config['MODEL_FOLDER'])
    except TrainingError as exc:
        return str(exc), 400
    return redirect(url_for('classification.index'))
