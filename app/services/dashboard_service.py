"""Queries shared by the Dashboard and its dataset upload modal."""
from sqlalchemy import func

from app.extensions import db
from app.models import Comment, Dataset


def dashboard_context(user_id):
    datasets_query = db.select(Dataset).filter_by(user_id=user_id)
    dataset = db.session.execute(
        datasets_query.order_by(Dataset.id.desc())
    ).scalars().first()
    count = None
    labels = {}
    preview = []
    if dataset:
        count = db.session.scalar(
            db.select(func.count(Comment.id)).filter_by(dataset_id=dataset.id)
        )
        labels = dict(db.session.execute(
            db.select(Comment.sentiment_label, func.count(Comment.id))
            .filter(
                Comment.dataset_id == dataset.id,
                Comment.sentiment_label.is_not(None),
            )
            .group_by(Comment.sentiment_label)
        ).all())
        preview = db.session.execute(
            db.select(Comment)
            .filter_by(dataset_id=dataset.id)
            .order_by(Comment.row_number)
            .limit(10)
        ).scalars().all()
    return {
        "dataset": dataset,
        "count": count,
        "labels": labels,
        "preview": preview,
    }
