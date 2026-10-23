"""Authenticated single and CSV batch inference."""
from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required
from app.extensions import db
from app.models import ModelRun, Prediction
from app.services.prediction_service import PredictionError, predict_single, predict_batch
from app.services.training_service import TrainingError, load_run

bp = Blueprint('testing', __name__)


def latest_run():
    return db.session.execute(db.select(ModelRun).filter_by(user_id=current_user.id, status='completed').order_by(ModelRun.id.desc())).scalars().first()


@bp.get('/testing')
@login_required
def index():
    return render_template('testing/index.html', run=latest_run())


@bp.post('/testing/single')
@login_required
def single():
    run = latest_run()
    if not run:
        return render_template('testing/index.html', run=None, error='Latih model terlebih dahulu'), 400
    text = request.form.get('comment', '')
    try:
        model, vectorizer = load_run(run, current_app.config['MODEL_FOLDER'])
        label = predict_single(text, model, vectorizer)
    except (PredictionError, TrainingError) as exc:
        return render_template('testing/index.html', run=run, error=str(exc)), 400
    db.session.add(Prediction(user_id=current_user.id, model_run_id=run.id, input_text=text, predicted_label=label))
    db.session.commit()
    return render_template('testing/index.html', run=run, single_label=label)


@bp.post('/testing/batch')
@login_required
def batch():
    run = latest_run()
    if not run:
        return render_template('testing/index.html', run=None, error='Latih model terlebih dahulu'), 400
    file = request.files.get('file')
    if not file or not file.filename or not file.filename.lower().endswith('.csv'):
        return render_template('testing/index.html', run=run, error='Pilih berkas CSV valid'), 400
    try:
        model, vectorizer = load_run(run, current_app.config['MODEL_FOLDER'])
        result = predict_batch(file.stream, request.form.get('comment_column', ''), model, vectorizer)
    except (PredictionError, TrainingError) as exc:
        return render_template('testing/index.html', run=run, error=str(exc)), 400
    for row in result['rows']:
        db.session.add(Prediction(user_id=current_user.id, model_run_id=run.id,
                                  input_text=row['text'], predicted_label=row['predicted_label'], row_number=row['row_number']))
    db.session.commit()
    return render_template('testing/index.html', run=run, batch_result=result)
