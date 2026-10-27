"""Independent manual holdout: eligibility, marking and readiness summary.

The training service only accepts test rows that carry a manual label and were
flagged by a Superadmin, so this module owns the single rule for both:
``manual_label`` must equal ``sentiment_label`` and ``label_source`` must be
``manual``. Nothing here invents labels; a comment without a manual label can
never become test data.
"""
from app.extensions import db
from app.models import Comment, User

LABELS = ('Positif', 'Negatif', 'Netral')


class HoldoutError(ValueError):
    pass


def is_eligible(comment):
    """True when the comment already has a valid manual label to hold out."""
    return bool(
        comment.manual_label
        and comment.label_source == 'manual'
        and comment.sentiment_label == comment.manual_label
    )


def set_holdout(comment, admin_id, value):
    """Flag or unflag a comment as independent test data (Superadmin only)."""
    admin = db.session.get(User, admin_id)
    if not admin or admin.role != 'superadmin':
        raise PermissionError('Hanya Superadmin boleh menetapkan data uji independen')
    if value and not is_eligible(comment):
        raise HoldoutError(
            'Beri label manual pada komentar ini sebelum menandainya sebagai data uji independen'
        )
    comment.is_independent_holdout = bool(value)
    db.session.commit()


def summary(dataset_id):
    """Counts for the UI: marked rows per class, missing classes, spare candidates."""
    rows = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id)).scalars().all()
    marked = [comment for comment in rows if comment.is_independent_holdout]
    per_class = {label: 0 for label in LABELS}
    for comment in marked:
        if comment.manual_label in per_class:
            per_class[comment.manual_label] += 1
    missing = [label for label in LABELS if per_class[label] < 1]
    return {
        'total': len(marked),
        'per_class': per_class,
        'missing': missing,
        'eligible': sum(1 for c in rows if not c.is_independent_holdout and is_eligible(c)),
        'ready': not missing,
    }
