import json
import os
from pathlib import Path

import joblib
import pytest
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, ModelRun, Prediction, User
from app.services.preprocessing_service import PREPROCESSING_VERSION
from app.services.training_service import (
    CLASSES, create_split, dataset_eligibility, load_run,
    run_evaluation, run_tfidf, run_training,
)


@pytest.fixture
def records(monkeypatch, tmp_path):
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL MySQL terpisah belum tersedia')
    from sqlalchemy.engine import make_url
    if make_url(url).database != 'sentiment_freeport_test':
        pytest.fail('TEST_DATABASE_URL wajib menunjuk sentiment_freeport_test')
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('MODEL_FOLDER', str(tmp_path / 'models'))
    app = create_app()
    with app.app_context():
        db.create_all()
        try:
            owner = User(full_name='Peneliti', email='stages@test.local')
            owner.set_password('secure-password-123')
            db.session.add(owner)
            db.session.flush()
            dataset = Dataset(
                user_id=owner.id, original_filename='stages.csv',
                stored_filename='stages-private.csv', file_path='private',
                row_count=36, comment_column='isi', status='processed',
            )
            db.session.add(dataset)
            db.session.flush()

            row_number = 2
            suffixes = ('satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan', 'sembilan', 'sepuluh')
            for label in ('Negatif', 'Netral', 'Positif'):
                for suffix in suffixes:
                    db.session.add(Comment(
                        dataset_id=dataset.id, row_number=row_number,
                        comment_text=f'{label} tambang {suffix}',
                        cleaned_text=f'{label.lower()} tambang {suffix}',
                        preprocessing_version=PREPROCESSING_VERSION,
                        sentiment_label=label, label_source='lexicon',
                    ))
                    row_number += 1

            for duplicate in range(2):
                db.session.add(Comment(
                    dataset_id=dataset.id, row_number=row_number,
                    comment_text=f'duplikat negatif {duplicate}',
                    cleaned_text='negatif tambang satu',
                    preprocessing_version=PREPROCESSING_VERSION,
                    sentiment_label='Negatif', label_source='lexicon',
                ))
                row_number += 1

            db.session.add(Comment(
                dataset_id=dataset.id, row_number=row_number,
                comment_text='review positif', cleaned_text='review positif',
                preprocessing_version=PREPROCESSING_VERSION,
                sentiment_label='Positif', label_source='review',
                review_status='review',
            ))
            row_number += 1
            db.session.add(Comment(
                dataset_id=dataset.id, row_number=row_number,
                comment_text='tanpa label final', cleaned_text='tanpa label final',
                preprocessing_version=PREPROCESSING_VERSION,
                sentiment_label=None,
            ))
            row_number += 1
            db.session.add(Comment(
                dataset_id=dataset.id, row_number=row_number,
                comment_text='teks kosong', cleaned_text='',
                preprocessing_version=PREPROCESSING_VERSION,
                sentiment_label='Positif', label_source='lexicon',
            ))
            db.session.commit()
            yield app, owner.id, dataset.id
        finally:
            db.session.remove()
            db.drop_all()


def login(app):
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.post('/login', data={
        'email': 'stages@test.local', 'password': 'secure-password-123',
    })
    assert response.status_code == 302
    return client


def comments_by_ids(ids):
    rows = db.session.execute(
        db.select(Comment).filter(Comment.id.in_(ids))
    ).scalars().all()
    return {int(comment.id): comment for comment in rows}


def test_split_ratios_are_stratified_deterministic_and_exclude_review(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        info = dataset_eligibility(dataset_id)
        assert info['counts'] == {'Negatif': 10, 'Netral': 10, 'Positif': 10}
        assert info['raw'] == 32
        assert info['unique'] == 30
        assert info['duplicates'] == 2
        assert info['ready'] is True

        first = create_split(dataset_id, owner_id, '70:30')
        second = create_split(dataset_id, owner_id, '70:30')
        assert first.split_indices == second.split_indices
        assert first.split_ratio == '70:30'
        assert first.random_state == 42
        assert first.split_config['stratified'] is True
        assert first.train_size + first.test_size == 30
        assert first.test_size == 9
        for label in CLASSES:
            assert first.train_distribution[label] == 7
            assert first.test_distribution[label] == 3

        all_ids = set(first.split_indices['train'] + first.split_indices['test'])
        rows = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id)).scalars().all()
        duplicate_ids = {int(c.id) for c in rows if c.cleaned_text == 'negatif tambang satu'}
        assert len(all_ids & duplicate_ids) == 1
        excluded_ids = {
            int(c.id) for c in rows
            if c.review_status == 'review' or c.sentiment_label is None or not (c.cleaned_text or '').strip()
        }
        assert not (all_ids & excluded_ids)

        for ratio, expected_test in (
            ('70:30', 9), ('80:20', 6), ('90:10', 3),
        ):
            run = create_split(dataset_id, owner_id, ratio)
            assert run.split_ratio == ratio
            assert run.train_size + run.test_size == 30
            assert run.test_size == expected_test
            for label in CLASSES:
                assert run.train_distribution[label] > 0
                assert run.test_distribution[label] > 0
                assert run.train_distribution[label] + run.test_distribution[label] == 10


def test_tfidf_fit_only_on_training_rows(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        run = create_split(dataset_id, owner_id, '70:30')
        run_tfidf(run, app.config['MODEL_FOLDER'])
        assert run.tfidf_at is not None
        assert run.tfidf_vocabulary_size > 0
        assert run.tfidf_train_shape[0] == run.train_size
        assert run.tfidf_test_shape[0] == run.test_size
        assert run.tfidf_train_shape[1] == run.tfidf_vocabulary_size
        assert run.tfidf_test_shape[1] == run.tfidf_vocabulary_size

        train_ids = [int(value) for value in run.split_indices['train']]
        test_ids = [int(value) for value in run.split_indices['test']]
        train_rows = comments_by_ids(train_ids)
        test_rows = comments_by_ids(test_ids)
        train_texts = [train_rows[index].cleaned_text for index in train_ids]
        test_texts = [test_rows[index].cleaned_text for index in test_ids]
        assert not (set(train_texts) & set(test_texts))

        reference = TfidfVectorizer().fit(train_texts)
        saved = joblib.load(run.vectorizer_path)
        assert saved.vocabulary_ == reference.vocabulary_

        folder = Path(run.vectorizer_path).parent
        x_train = sparse.load_npz(folder / 'train_matrix.npz')
        x_test = sparse.load_npz(folder / 'test_matrix.npz')
        assert x_train.shape == tuple(run.tfidf_train_shape)
        assert x_test.shape == tuple(run.tfidf_test_shape)


def test_training_and_evaluation_use_saved_artifacts(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        run = create_split(dataset_id, owner_id, '70:30')
        run_tfidf(run, app.config['MODEL_FOLDER'])
        run_training(run, app.config['MODEL_FOLDER'])
        run_evaluation(run, app.config['MODEL_FOLDER'])

        assert run.status == 'completed'
        assert run.trained_at is not None
        assert run.evaluated_at is not None
        assert Path(run.model_path).is_file()
        assert Path(run.vectorizer_path).is_file()
        assert run.test_count == run.test_size

        model, vectorizer = load_run(run, app.config['MODEL_FOLDER'])
        assert model.predict(vectorizer.transform(['tambang positif'])).shape == (1,)

        folder = Path(run.model_path).parent
        x_test = sparse.load_npz(folder / 'test_matrix.npz')
        y_test = json.loads((folder / 'test_labels.json').read_text(encoding='utf-8'))
        predicted = model.predict(x_test)
        assert float(run.accuracy) == pytest.approx(accuracy_score(y_test, predicted))
        assert run.confusion_matrix == confusion_matrix(y_test, predicted, labels=CLASSES).tolist()
        assert sum(run.prediction_distribution.values()) == run.test_count == len(y_test)
        assert run.classification_report['accuracy'] == pytest.approx(float(run.accuracy))


def test_stage_routes_require_dependencies(records):
    app, owner_id, dataset_id = records
    client = login(app)

    response = client.post('/classification/tfidf', data={'dataset_id': dataset_id})
    assert response.status_code == 400
    assert 'Split Data belum dijalankan' in response.data.decode()

    assert client.post('/classification/split', data={
        'dataset_id': dataset_id, 'split_ratio': '70:30',
    }).status_code == 302

    response = client.post('/classification/train', data={'dataset_id': dataset_id})
    assert response.status_code == 400
    assert 'TF-IDF belum dijalankan' in response.data.decode()

    assert client.post('/classification/tfidf', data={'dataset_id': dataset_id}).status_code == 302

    response = client.post('/classification/evaluate', data={'dataset_id': dataset_id})
    assert response.status_code == 400
    assert 'Training SVM belum dijalankan' in response.data.decode()

    assert client.post('/classification/train', data={'dataset_id': dataset_id}).status_code == 302
    assert client.post('/classification/evaluate', data={'dataset_id': dataset_id}).status_code == 302

    response = client.post('/classification/tfidf', data={'dataset_id': dataset_id})
    assert response.status_code == 400
    assert 'sudah dijalankan' in response.data.decode()


def test_testing_uses_latest_completed_model_without_retraining(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        run = create_split(dataset_id, owner_id, '70:30')
        run_tfidf(run, app.config['MODEL_FOLDER'])
        run_training(run, app.config['MODEL_FOLDER'])
        run_evaluation(run, app.config['MODEL_FOLDER'])
        run_id = run.id
        run_count = db.session.scalar(db.select(db.func.count(ModelRun.id)))

    db.session.remove()
    client = login(app)
    response = client.post('/testing/single', data={'comment': 'tambang positif'})
    assert response.status_code == 200
    assert 'Hasil Prediksi:' in response.data.decode()
    assert 'tambang positif' in response.data.decode()

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ModelRun.id))) == run_count
        prediction = db.session.execute(
            db.select(Prediction).filter_by(source='testing')
        ).scalar_one()
        assert prediction.model_run_id == run_id


def test_testing_uses_trained_model_before_evaluation(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        run = create_split(dataset_id, owner_id, '70:30')
        run_tfidf(run, app.config['MODEL_FOLDER'])
        run_training(run, app.config['MODEL_FOLDER'])
        run_id = run.id
        assert run.status == 'trained'

    db.session.remove()
    client = login(app)
    response = client.post('/testing/single', data={'comment': 'tambang positif'})
    assert response.status_code == 200
    assert 'Hasil Prediksi:' in response.data.decode()
    assert 'tambang positif' in response.data.decode()

    with app.app_context():
        prediction = db.session.execute(
            db.select(Prediction).filter_by(source='testing')
        ).scalar_one()
        assert prediction.model_run_id == run_id


def test_split_excludes_stale_preprocessing_rows(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        stale = db.session.execute(
            db.select(Comment).filter_by(dataset_id=dataset_id, cleaned_text='positif tambang satu')
        ).scalar_one()
        stale.preprocessing_version = 'versi-lama'
        db.session.commit()
        info = dataset_eligibility(dataset_id)
        assert info['stale'] == 1
        assert info['ready'] is True

        run = create_split(dataset_id, owner_id, '70:30')
        split_ids = set(run.split_indices['train'] + run.split_indices['test'])
        assert stale.id not in split_ids


def test_split_supports_two_classes_and_warns_missing_neutral(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        neutral = db.session.execute(
            db.select(Comment).filter_by(dataset_id=dataset_id, sentiment_label='Netral')
        ).scalars().all()
        for comment in neutral:
            comment.sentiment_label = None
        db.session.commit()
        info = dataset_eligibility(dataset_id)
        assert info['ready'] is True
        assert info['active_classes'] == ['Negatif', 'Positif']
        assert info['missing'] == ['Netral']
        assert 'Netral' in info['warning']

        run = create_split(dataset_id, owner_id, '70:30')
        assert run.split_config['classes'] == ['Negatif', 'Positif']
        assert run.train_distribution['Netral'] == 0
        assert run.test_distribution['Netral'] == 0
        run_tfidf(run, app.config['MODEL_FOLDER'])
        run_training(run, app.config['MODEL_FOLDER'])
        run_evaluation(run, app.config['MODEL_FOLDER'])
        assert len(run.confusion_matrix) == 2
        assert 'Netral' not in run.prediction_distribution
        assert {'Negatif', 'Positif'} <= set(run.classification_report)
