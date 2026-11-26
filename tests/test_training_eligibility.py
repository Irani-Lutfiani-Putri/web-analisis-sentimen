import os

import pytest

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, User
from app.services.preprocessing_service import PREPROCESSING_VERSION
from app.services.training_service import CLASSES, create_split, dataset_eligibility


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
        try:
            owner = User(full_name='Admin', email='eligibility@test.local')
            owner.set_password('secure-password-123')
            db.session.add(owner)
            db.session.flush()
            dataset = Dataset(
                user_id=owner.id, original_filename='uji.csv',
                stored_filename='eligibility.csv', file_path='private',
                row_count=14, comment_column='isi', status='processed',
            )
            db.session.add(dataset)
            db.session.flush()
            row_number = 2
            for label in ('Negatif', 'Netral', 'Positif'):
                for index in range(4):
                    db.session.add(Comment(
                        dataset_id=dataset.id, row_number=row_number,
                        comment_text=f'{label} tambang {index}',
                        cleaned_text=f'{label.lower()} tambang {index}',
                        preprocessing_version=PREPROCESSING_VERSION,
                        sentiment_label=label, label_source='lexicon',
                    ))
                    row_number += 1
            review = Comment(
                dataset_id=dataset.id, row_number=row_number,
                comment_text='review positif', cleaned_text='review positif',
                preprocessing_version=PREPROCESSING_VERSION,
                sentiment_label='Positif', label_source='review',
                review_status='review',
            )
            db.session.add(review)
            row_number += 1
            unlabeled = Comment(
                dataset_id=dataset.id, row_number=row_number,
                comment_text='tanpa label', cleaned_text='tanpa label',
                preprocessing_version=PREPROCESSING_VERSION,
                sentiment_label=None,
            )
            db.session.add(unlabeled)
            db.session.commit()
            yield app, owner.id, dataset.id, review.id, unlabeled.id
        finally:
            db.session.remove()
            db.drop_all()


def test_eligibility_ignores_review_and_unlabeled_rows(records):
    app, owner_id, dataset_id, review_id, unlabeled_id = records
    with app.app_context():
        info = dataset_eligibility(dataset_id)
        assert info['counts'] == {label: 4 for label in CLASSES}
        assert info['raw'] == 12
        assert info['unique'] == 12
        assert info['ready'] is True
        run = create_split(dataset_id, owner_id, '70:30')
        split_ids = set(run.split_indices['train'] + run.split_indices['test'])
        assert run.train_size + run.test_size == 12
        assert review_id not in split_ids
        assert unlabeled_id not in split_ids
