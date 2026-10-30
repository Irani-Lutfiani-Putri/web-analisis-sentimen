"""Shared comment listing rules for Preprocessing and Kelola Dataset.

One module owns three decisions so the two pages can never drift apart:
which filter keys a role may use, which rows a role may see, and how a
page of comments is sliced. Rows still awaiting Superadmin review are
filtered here — in SQL, before pagination — so page counts stay honest
instead of hiding rows after the fact.
"""
from flask import abort
from flask_login import current_user

from app.extensions import db
from app.models import Comment, Dataset

PAGE_SIZE = 10

LABEL_FILTERS = {'positif': 'Positif', 'negatif': 'Negatif', 'netral': 'Netral'}

# `review` rows have no reliable label yet; only Superadmin may see them.
USER_FILTER_KEYS = {'semua', 'sudah', *LABEL_FILTERS}
ADMIN_FILTER_KEYS = {'semua', 'sudah', 'review', 'manual', 'lexicon', *LABEL_FILTERS}

FILTER_TEXTS = {
    'semua': 'Semua label',
    'sudah': 'Sudah dilabelkan',
    'positif': 'Positif',
    'negatif': 'Negatif',
    'netral': 'Netral',
    'review': 'Perlu review',
    'manual': 'Label manual',
    'lexicon': 'Label otomatis',
}

# Order matters: it is the order of the <option> list in both pages.
USER_FILTER_ORDER = ('semua', 'sudah', 'positif', 'negatif', 'netral')
ADMIN_FILTER_ORDER = ('semua', 'sudah', 'positif', 'negatif', 'netral', 'review', 'manual', 'lexicon')


def is_superadmin(role=None):
    return (role if role is not None else current_user.role) == 'superadmin'


def allowed_filter_keys(role):
    return ADMIN_FILTER_KEYS if is_superadmin(role) else USER_FILTER_KEYS


def filter_order(role):
    return ADMIN_FILTER_ORDER if is_superadmin(role) else USER_FILTER_ORDER


def normalize_filter(label, role):
    """Unknown or forbidden filters fall back to 'semua' rather than 403."""
    return label if label in allowed_filter_keys(role) else 'semua'


def filter_options(role):
    return [{'value': key, 'text': FILTER_TEXTS[key]} for key in filter_order(role)]


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


def build_query(dataset_id, q, label, role):
    """Base SELECT for a dataset, already narrowed to what `role` may see."""
    query = db.select(Comment).filter(Comment.dataset_id == dataset_id)
    if not is_superadmin(role):
        # Rows queued for review stay invisible to regular users. Imported
        # manual rows carry review_status NULL, hence the coalesce.
        query = query.filter(db.func.coalesce(Comment.review_status, '') != 'review')
    if q:
        query = query.filter(Comment.comment_text.like(f"%{q}%"))
    if label == 'review':
        query = query.filter(Comment.review_status == 'review')
    elif label == 'manual':
        query = query.filter(Comment.label_source == 'manual')
    elif label == 'lexicon':
        query = query.filter(Comment.label_source == 'lexicon')
    elif label == 'sudah':
        query = query.filter(Comment.sentiment_label.is_not(None))
    elif label in LABEL_FILTERS:
        query = query.filter(Comment.sentiment_label == LABEL_FILTERS[label])
    return query


def paginate(dataset_id, q, label, role, page_arg):
    base = build_query(dataset_id, q, label, role)
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
    """How many rows are waiting for Superadmin; shown to users as a number only."""
    return db.session.scalar(
        db.select(db.func.count(Comment.id))
        .filter(Comment.dataset_id == dataset_id, Comment.review_status == 'review')
    ) or 0
