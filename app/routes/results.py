"""Read-only result page for completed SVM experiments."""
from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.services.results_service import build_results_context

bp = Blueprint('results', __name__)


@bp.get('/results')
@login_required
def index():
    page = max(1, request.args.get('page', type=int) or 1)
    dataset_id = request.args.get('dataset_id', type=int)
    return render_template(
        'results/index.html',
        **build_results_context(dataset_id, current_user.id, page),
    )
