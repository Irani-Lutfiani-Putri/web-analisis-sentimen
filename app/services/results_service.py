"""Read-only views for completed SVM experiments."""
from app.extensions import db
from app.models import Comment, Dataset, ModelRun, Prediction
from app.services.preprocessing_service import PREPROCESSING_VERSION
from app.services.training_service import CLASSES

DISPLAY_CLASSES = ['Positif', 'Netral', 'Negatif']
PAGE_SIZE = 10


def latest_completed_run(dataset_id, owner_id):
    query = db.select(ModelRun).filter(
        ModelRun.user_id == owner_id,
        ModelRun.status == 'completed',
        ModelRun.evaluated_at.is_not(None),
    )
    if dataset_id:
        query = query.filter(ModelRun.dataset_id == dataset_id)
    return db.session.execute(query.order_by(ModelRun.id.desc())).scalars().first()


def _dataset(dataset_id, owner_id):
    if not dataset_id:
        return None
    return db.session.execute(
        db.select(Dataset).filter_by(id=dataset_id, user_id=owner_id)
    ).scalars().first()


def _run_classes(run):
    return (run.split_config or {}).get('classes', CLASSES)


def _matrix_3(run):
    matrix = [[0 for _ in DISPLAY_CLASSES] for _ in DISPLAY_CLASSES]
    run_classes = _run_classes(run)
    stored = run.confusion_matrix or []
    for actual_index, actual in enumerate(run_classes):
        for predicted_index, predicted in enumerate(run_classes):
            if actual not in DISPLAY_CLASSES or predicted not in DISPLAY_CLASSES:
                continue
            if actual_index < len(stored) and predicted_index < len(stored[actual_index]):
                matrix[DISPLAY_CLASSES.index(actual)][DISPLAY_CLASSES.index(predicted)] = int(
                    stored[actual_index][predicted_index]
                )
    return matrix


def _report_rows(run):
    report = run.classification_report or {}
    rows = []
    for label in DISPLAY_CLASSES:
        data = report.get(label)
        support = int(data.get('support', 0)) if data else 0
        available = bool(data and support)
        rows.append({
            'label': label,
            'available': available,
            'precision': float(data['precision']) if available else None,
            'recall': float(data['recall']) if available else None,
            'f1': float(data['f1-score']) if available else None,
            'support': support,
        })
    return rows


def _preprocessing_version(run):
    version = (run.split_config or {}).get('preprocessing_version')
    if version:
        return version
    version = db.session.execute(
        db.select(Comment.preprocessing_version)
        .join(Prediction, Prediction.comment_id == Comment.id)
        .filter(Prediction.model_run_id == run.id, Prediction.source == 'evaluation')
        .limit(1)
    ).scalar()
    return version or 'Tidak tercatat'


def _distribution(values):
    values = values or {}
    return {label: int(values.get(label, 0)) for label in DISPLAY_CLASSES}


def _prediction_rows(run, page, page_size=PAGE_SIZE):
    base = db.select(Prediction, Comment).join(
        Comment, Prediction.comment_id == Comment.id
    ).filter(
        Prediction.model_run_id == run.id,
        Prediction.source == 'evaluation',
    )
    total = db.session.scalar(db.select(db.func.count()).select_from(base.subquery()))
    total_pages = max(1, -(-total // page_size))
    page = min(max(page or 1, 1), total_pages)
    rows = db.session.execute(
        base.order_by(Prediction.row_number.asc(), Prediction.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    start = (page - 1) * page_size
    for offset, (prediction, comment) in enumerate(rows, start=1):
        items.append({
            'number': start + offset,
            'original': comment.comment_text,
            'cleaned': comment.cleaned_text,
            'actual': prediction.actual_label,
            'predicted': prediction.predicted_label,
            'correct': prediction.actual_label == prediction.predicted_label,
        })
    return items, int(total), page, total_pages


def build_results_context(dataset_id, owner_id, page):
    selected_dataset = _dataset(dataset_id, owner_id)
    run = latest_completed_run(dataset_id, owner_id)
    context = {
        'run': run,
        'selected_dataset': selected_dataset,
        'display_classes': DISPLAY_CLASSES,
        'page_size': PAGE_SIZE,
        'page': 1,
        'total_pages': 1,
        'predictions': [],
        'total_predictions': 0,
        'matrix': [],
        'report_rows': [],
        'prediction_distribution': {label: 0 for label in DISPLAY_CLASSES},
        'overall_distribution': {label: 0 for label in DISPLAY_CLASSES},
        'test_distribution': {label: 0 for label in DISPLAY_CLASSES},
        'used_rows': 0,
        'raw_rows': 0,
        'duplicates': 0,
        'conflicts': 0,
        'preprocessing_version': None,
        'current_version': PREPROCESSING_VERSION,
        'version_stale': False,
        'test_count': 0,
        'test_count_mismatch': False,
        'distribution_mismatch': False,
        'run_classes': [],
        'missing_result_classes': DISPLAY_CLASSES,
    }
    if not run:
        return context

    dataset = selected_dataset or db.session.get(Dataset, run.dataset_id)
    selected_dataset = dataset if dataset and dataset.user_id == owner_id else None
    run_classes = _run_classes(run)
    preprocessing_version = _preprocessing_version(run)
    overall_distribution = {
        label: int((run.train_distribution or {}).get(label, 0))
        + int((run.test_distribution or {}).get(label, 0))
        for label in DISPLAY_CLASSES
    }
    prediction_distribution = _distribution(run.prediction_distribution)
    test_distribution = _distribution(run.test_distribution)
    predictions, total_predictions, page, total_pages = _prediction_rows(run, page)
    test_count = int(run.test_count or 0)
    used_rows = int(run.train_size or 0) + int(run.test_size or 0)
    split_config = run.split_config or {}
    context.update({
        'selected_dataset': selected_dataset,
        'run_classes': run_classes,
        'missing_result_classes': [label for label in DISPLAY_CLASSES if label not in run_classes],
        'matrix': _matrix_3(run),
        'report_rows': _report_rows(run),
        'prediction_distribution': prediction_distribution,
        'overall_distribution': overall_distribution,
        'test_distribution': test_distribution,
        'predictions': predictions,
        'total_predictions': total_predictions,
        'page': page,
        'total_pages': total_pages,
        'used_rows': used_rows,
        'raw_rows': int(split_config.get('raw_rows', used_rows)),
        'duplicates': int(split_config.get('duplicates', 0)),
        'conflicts': int(split_config.get('conflicts', 0)),
        'preprocessing_version': preprocessing_version,
        'version_stale': preprocessing_version != PREPROCESSING_VERSION,
        'test_count': test_count,
        'test_count_mismatch': total_predictions != test_count,
        'distribution_mismatch': sum(prediction_distribution.values()) != test_count,
    })
    return context
