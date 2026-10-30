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
        return render_template(
            'testing/index.html', run=run,
            field_errors={'comment': str(exc)},
            form_values={'comment': text},
        ), 400
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
    comment_column = request.form.get('comment_column', '')
    values = {'comment_column': comment_column}
    if not file or not file.filename or not file.filename.lower().endswith('.csv'):
        return render_template(
            'testing/index.html', run=run,
            field_errors={'batch_file': 'Pilih berkas CSV valid.'},
            form_values=values,
        ), 400
    try:
        model, vectorizer = load_run(run, current_app.config['MODEL_FOLDER'])
        result = predict_batch(file.stream, comment_column, model, vectorizer)
    except PredictionError as exc:
        field = 'comment_column' if exc.field == 'comment_column' else 'batch_file'
        return render_template(
            'testing/index.html', run=run,
            field_errors={field: str(exc)}, form_values=values,
        ), 400
    except TrainingError as exc:
        return render_template(
            'testing/index.html', run=run, error=str(exc), form_values=values,
        ), 400
    for row in result['rows']:
        db.session.add(Prediction(user_id=current_user.id, model_run_id=run.id,
                                  input_text=row['text'], predicted_label=row['predicted_label'], row_number=row['row_number']))
    db.session.commit()
    page = max(1, request.args.get('page', type=int) or 1)
    page_size = 10
    total_rows = len(result['rows'])
    total_pages = max(1, -(-total_rows // page_size))
    page = min(page, total_pages)
    start = (page - 1) * page_size
    paged = {**result, 'rows': result['rows'][start:start + page_size]}
    return render_template('testing/index.html', run=run, batch_result=result,
                           batch_rows=paged['rows'], batch_page=page, batch_total_pages=total_pages,
                           batch_total_rows=total_rows)
