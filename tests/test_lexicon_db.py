import os

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import User, Dataset, Comment, LabelHistory
from app.services import lexicon_service
from app.services.holdout_service import set_holdout
from app.services.lexicon_service import annotate_dataset, update_manual_label


@pytest.fixture
def records(monkeypatch):
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL MySQL terpisah belum tersedia')
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    with app.app_context():
        db.create_all()
        owner = User(full_name='Pemilik', email='owner@research.test')
        owner.set_password('secure-password-123')
        db.session.add(owner); db.session.flush()
        dataset = Dataset(user_id=owner.id, original_filename='uji.csv', stored_filename='uji-internal.csv', file_path='private', row_count=3, comment_column='text', status='validated')
        db.session.add(dataset); db.session.flush()
        db.session.add_all([
            Comment(dataset_id=dataset.id, row_number=2, comment_text='baik', manual_label='Negatif', sentiment_label='Negatif', label_source='manual', labeled_by=owner.id),
            Comment(dataset_id=dataset.id, row_number=3, comment_text='buruk'),
            Comment(dataset_id=dataset.id, row_number=4, comment_text='tidak buruk'),
        ])
        db.session.commit()
        yield app, dataset.id, owner.id
        db.session.remove(); db.drop_all()


def test_lexicon_preserves_manual_and_reviews_negation(records):
    app, dataset_id, admin_id = records
    with app.app_context():
        result = annotate_dataset(dataset_id, {'baik':3, 'buruk':-3}, 'test-lexicon-v1')
        comments = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id).order_by(Comment.row_number)).scalars().all()
        assert result == {'processed': 2, 'review': 1}
        assert comments[0].manual_label == comments[0].sentiment_label == 'Negatif'
        assert comments[0].lexicon_label is None
        assert comments[1].sentiment_label == 'Negatif'
        assert comments[1].lexicon_version == 'test-lexicon-v1'
        assert comments[2].sentiment_label is None and comments[2].review_status == 'review'


def test_manual_correction_records_history(records):
    app, dataset_id, owner_id = records
    with app.app_context():
        comment = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id, row_number=2)).scalar_one()
        update_manual_label(comment, 'Positif', owner_id, 'ditinjau ulang')
        assert comment.manual_label == comment.sentiment_label == 'Positif'
        history = db.session.execute(db.select(LabelHistory)).scalar_one()
        assert (history.previous_label, history.new_label, history.changed_by) == ('Negatif', 'Positif', owner_id)


def test_manual_holdout_does_not_require_role(records):
    app, dataset_id, _ = records
    with app.app_context():
        comment = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id, row_number=2)).scalar_one()
        set_holdout(comment, True)
        assert comment.is_independent_holdout is True


def test_manual_label_committed_during_annotation_wins(records, monkeypatch):
    app, dataset_id, _ = records
    with app.app_context():
        target = db.session.execute(
            db.select(Comment).filter_by(dataset_id=dataset_id, row_number=3)
        ).scalar_one()
        original = lexicon_service.classify_comment
        calls = {'count': 0}

        def racing_classify(comment_text, weights, conflicting_words=()):
            if calls['count'] == 0:
                with db.engine.begin() as connection:
                    connection.execute(
                        text(
                            "UPDATE comments SET manual_label='Negatif', "
                            "sentiment_label='Negatif', label_source='manual', "
                            "review_status='resolved' WHERE id=:comment_id"
                        ),
                        {'comment_id': target.id},
                    )
            calls['count'] += 1
            return original(comment_text, weights, conflicting_words)

        monkeypatch.setattr(lexicon_service, 'classify_comment', racing_classify)
        annotate_dataset(dataset_id, {'buruk': 3}, 'test-race')
        db.session.expire_all()
        saved = db.session.get(Comment, target.id)
        assert saved.manual_label == 'Negatif'
        assert saved.sentiment_label == 'Negatif'
        assert saved.label_source == 'manual'
