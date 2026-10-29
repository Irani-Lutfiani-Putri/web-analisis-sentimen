import os
import pytest
from pathlib import Path
from app import create_app
from app.extensions import db
from app.models import User, Dataset, Comment, ModelRun
from app.services.training_service import train_dataset, TrainingError, load_run


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
            owner = User(full_name='Peneliti', email='train@test.local', role='user')
            owner.set_password('secure-password-123')
            db.session.add(owner); db.session.flush()
            dataset = Dataset(user_id=owner.id, original_filename='train.csv', stored_filename='train-private.csv', file_path='private', row_count=24, comment_column='text', status='processed')
            db.session.add(dataset); db.session.flush()
            suffixes = ('satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan')
            for group, label in enumerate(('Negatif','Netral','Positif')):
                for n, suffix in enumerate(suffixes):
                    db.session.add(Comment(dataset_id=dataset.id, row_number=group*8+n+2,
                        comment_text=f'{label} tambang {suffix}', cleaned_text=f'{label.lower()} tambang {suffix}',
                        manual_label=label if n==0 else None, is_independent_holdout=(n==0),
                        sentiment_label=label, label_source='manual' if n==0 else 'lexicon'))
            db.session.commit()
            yield app, owner.id, dataset.id
        finally:
            db.session.remove(); db.drop_all()


def test_train_dataset_saves_real_metrics_and_reloadable_pair(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        run = train_dataset(dataset_id, owner_id, app.config['MODEL_FOLDER'])
        assert run.status == 'completed'
        assert run.dataset_id == dataset_id
        assert run.confusion_matrix is not None
        assert len(run.confusion_matrix) == 3
        assert all(len(row)==3 for row in run.confusion_matrix)
        model, vectorizer = load_run(run, app.config['MODEL_FOLDER'])
        assert model.predict(vectorizer.transform(['tambang positif'])).shape == (1,)
        assert Path(run.model_path).is_file() and Path(run.vectorizer_path).is_file()
        assert db.session.execute(db.select(ModelRun)).scalar_one().id == run.id


def test_training_error_renders_dataset_field(records):
    app, owner_id, dataset_id = records
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    client.post('/login', data={'email': 'train@test.local', 'password': 'secure-password-123'})
    response = client.post('/classification/train', data={'dataset_id': ''})
    assert response.status_code == 400
    assert b'id="dataset_id-error"' in response.data
    assert b'Klasifikasi SVM' in response.data


def test_training_and_inference_routes_with_mysql(records):
    from io import BytesIO
    app, owner_id, dataset_id = records
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    login = client.post('/login', data={'email': 'train@test.local', 'password': 'secure-password-123'})
    assert login.status_code == 302
    assert client.post('/testing/single', data={'comment': 'tambang positif'}).status_code == 400
    trained = client.post('/classification/train', data={'dataset_id': dataset_id})
    assert trained.status_code == 302
    empty_single = client.post('/testing/single', data={'comment': ''})
    assert empty_single.status_code == 400
    assert b'id="comment-error"' in empty_single.data
    missing_batch = client.post('/testing/batch', data={'comment_column': ''}, content_type='multipart/form-data')
    assert missing_batch.status_code == 400
    assert b'id="batch_file-error"' in missing_batch.data
    invalid_column = client.post('/testing/batch', data={
        'comment_column': 'salah',
        'file': (BytesIO(b'isi\ntambang positif\n'), 'uji.csv'),
    }, content_type='multipart/form-data')
    assert invalid_column.status_code == 400
    assert b'id="comment_column-error"' in invalid_column.data
    page = client.get('/classification')
    assert page.status_code == 200
    assert b'Confusion matrix' in page.data
    single = client.post('/testing/single', data={'comment': 'tambang positif'})
    assert single.status_code == 200
    assert b'Prediksi:' in single.data
    batch = client.post('/testing/batch', data={
        'comment_column': 'isi',
        'file': (BytesIO(b'isi\ntambang positif\n" "\ntambang negatif\n'), 'uji.csv'),
    }, content_type='multipart/form-data')
    assert batch.status_code == 200
    assert b'2 komentar valid; 1 ditolak' in batch.data
    with app.app_context():
        from app.models import Prediction
        assert db.session.scalar(db.select(db.func.count(Prediction.id))) == 3


def test_holdout_ignores_conflicting_lexicon_score(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        comments = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id).order_by(Comment.id)).scalars().all()
        manual = [c for c in comments if c.manual_label]
        manual[0].lexicon_label = 'Positif' if manual[0].manual_label != 'Positif' else 'Negatif'
        manual[0].lexicon_score = -5
        db.session.commit()
        run = train_dataset(dataset_id, owner_id, app.config['MODEL_FOLDER'])
        assert run.status == 'completed'


def test_train_rejects_no_independent_manual_holdout(records):
    app, owner_id, dataset_id = records
    with app.app_context():
        for comment in db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id)).scalars():
            comment.manual_label = None
        db.session.commit()
        with pytest.raises(TrainingError, match='manual'):
            train_dataset(dataset_id, owner_id, app.config['MODEL_FOLDER'])
        assert db.session.execute(db.select(ModelRun)).first() is None
