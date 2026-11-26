import os
from io import BytesIO

import pytest

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, ModelRun, Prediction, User
from app.services.preprocessing_service import PREPROCESSING_VERSION


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
            owner = User(full_name='Peneliti', email='train@test.local')
            owner.set_password('secure-password-123')
            db.session.add(owner)
            db.session.flush()
            dataset = Dataset(
                user_id=owner.id, original_filename='train.csv',
                stored_filename='train-private.csv', file_path='private',
                row_count=30, comment_column='text', status='processed',
            )
            db.session.add(dataset)
            db.session.flush()
            suffixes = ('satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan', 'sembilan', 'sepuluh')
            row_number = 2
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
            db.session.commit()
            yield app, owner.id, dataset.id
        finally:
            db.session.remove()
            db.drop_all()


def login(app):
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.post('/login', data={
        'email': 'train@test.local', 'password': 'secure-password-123',
    })
    assert response.status_code == 302
    return client


def test_training_error_renders_dataset_field(records):
    app, owner_id, dataset_id = records
    client = login(app)
    response = client.post('/classification/train', data={'dataset_id': ''})
    assert response.status_code == 400
    assert b'id="dataset_id-error"' in response.data
    assert b'Klasifikasi SVM' in response.data


def test_staged_training_and_inference_routes_with_mysql(records):
    app, owner_id, dataset_id = records
    client = login(app)
    assert client.post('/testing/single', data={'comment': 'tambang positif'}).status_code == 400

    assert client.post('/classification/split', data={
        'dataset_id': dataset_id, 'split_ratio': '70:30',
    }).status_code == 302
    assert client.post('/classification/tfidf', data={'dataset_id': dataset_id}).status_code == 302
    assert client.post('/classification/train', data={'dataset_id': dataset_id}).status_code == 302
    assert client.post('/classification/evaluate', data={'dataset_id': dataset_id}).status_code == 302

    page = client.get(f'/classification?dataset_id={dataset_id}')
    assert page.status_code == 200
    assert b'Confusion matrix' in page.data
    assert b'Classification Report' in page.data
    assert b'Accuracy' in page.data
    assert b'Lihat Hasil Klasifikasi' in page.data
    assert f'/results?dataset_id={dataset_id}'.encode() in page.data

    initial_testing = client.get('/testing')
    assert b'Cek Data Testing (Upload CSV)' in initial_testing.data
    assert b'Belum ada data diupload.' in initial_testing.data
    assert b'Total Data' in initial_testing.data

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

    single = client.post('/testing/single', data={'comment': 'tambang positif'})
    assert single.status_code == 200
    assert b'Hasil Prediksi:' in single.data
    assert b'Kalimat diuji:' in single.data
    assert b'tambang positif' in single.data
    assert any(
        f'testing-prediction-{label}'.encode() in single.data
        for label in ('positif', 'negatif', 'netral')
    )
    batch_rows = ['isi'] + [f'tambang memberi manfaat {index}' for index in range(12)] + ['" "']
    batch = client.post('/testing/batch', data={
        'comment_column': 'isi',
        'file': (BytesIO(('\n'.join(batch_rows) + '\n').encode()), 'uji.csv'),
    }, content_type='multipart/form-data')
    assert batch.status_code == 200
    assert b'12 komentar valid; 1 ditolak' in batch.data
    for index in range(12):
        assert f'tambang memberi manfaat {index}'.encode() in batch.data
    assert b'Halaman' not in batch.data

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ModelRun.id))) == 1
        run = db.session.execute(db.select(ModelRun)).scalar_one()
        assert db.session.scalar(
            db.select(db.func.count(Prediction.id)).filter_by(source='testing')
        ) == 13
        assert db.session.scalar(
            db.select(db.func.count(Prediction.id)).filter_by(source='evaluation')
        ) == run.test_count
