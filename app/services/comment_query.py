"""Shared comment listing rules for Preprocessing and the labels page.

Preprocessing shows only comments with a final label. The labels page shows
every row, including review and unlabeled rows, so a human can resolve them.
"""
from flask import abort
from flask_login import current_user

from app.extensions import db
from app.models import Comment, Dataset

PAGE_SIZE = 10

LABEL_FILTERS = {'positif': 'Positif', 'negatif': 'Negatif', 'netral': 'Netral'}

PREPROCESS_FILTER_KEYS = ('semua', 'sudah', *LABEL_FILTERS)
LABELS_FILTER_KEYS = ('semua', 'sudah', *LABEL_FILTERS, 'review', 'manual', 'lexicon')

FILTER_TEXTS = {
    'semua': 'Semua label',
    'sudah': 'Sudah dilabelkan',
    'positif': 'Positif',
    'negatif': 'Negatif',
    'netral': 'Netral',
    'review': 'Perlu label',
    'manual': 'Label manual',
    'lexicon': 'Label otomatis',
}


def normalize_filter(label, allowed_keys):
    """Unknown filters fall back to 'semua' rather than 403."""
    return label if label in allowed_keys else 'semua'


def filter_options(allowed_keys):
    return [{'value': key, 'text': FILTER_TEXTS[key]} for key in allowed_keys]


def format_score(value):
    if value is None:
        return None
    number = float(value)
    return f"{int(number)}" if number.is_integer() else f"{number:.2f}"


def owned_dataset(dataset_id):
    dataset = db.session.get(Dataset, dataset_id) if dataset_id else None
    if not dataset or dataset.user_id != current_user.id:
        abort(404)
    return dataset


def build_query(dataset_id, q, label, include_review=False):
    """Base SELECT for a dataset, narrowed to the page's visibility rule."""
    query = db.select(Comment).filter(Comment.dataset_id == dataset_id)
    if not include_review:
        # Imported manual rows carry review_status NULL, hence the coalesce.
        query = query.filter(
            Comment.sentiment_label.is_not(None),
            db.func.coalesce(Comment.review_status, '') != 'review',
        )
    if q:
        query = query.filter(Comment.comment_text.like(f"%{q}%"))
    if label == 'review':
        query = query.filter(
            db.or_(Comment.sentiment_label.is_(None), Comment.review_status == 'review')
        )
    elif label == 'manual':
        query = query.filter(Comment.label_source == 'manual')
    elif label == 'lexicon':
        query = query.filter(Comment.label_source == 'lexicon')
    elif label == 'sudah':
        query = query.filter(Comment.sentiment_label.is_not(None))
    elif label in LABEL_FILTERS:
        query = query.filter(Comment.sentiment_label == LABEL_FILTERS[label])
    return query


def paginate(dataset_id, q, label, page_arg, include_review=False):
    base = build_query(dataset_id, q, label, include_review=include_review)
    total_filtered = db.session.scalar(db.select(db.func.count()).select_from(base.subquery()))
    total_pages = max(1, -(-total_filtered // PAGE_SIZE))
    page = min(max(page_arg or 1, 1), total_pages)
    comments = db.session.execute(
        base.order_by(Comment.row_number).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    ).scalars().all()
    return comments, total_filtered, page, total_pages


def label_counts(dataset_id):
    return dict(db.session.execute(
        db.select(Comment.sentiment_label, db.func.count(Comment.id))
        .filter(Comment.dataset_id == dataset_id, Comment.sentiment_label.is_not(None))
        .group_by(Comment.sentiment_label)).all())


def pending_review_count(dataset_id):
    """Rows that still need a human label, including never-labeled imports."""
    return db.session.scalar(
        db.select(db.func.count(Comment.id))
        .filter(
            Comment.dataset_id == dataset_id,
            db.or_(Comment.sentiment_label.is_(None), Comment.review_status == 'review'),
        )
    ) or 0
