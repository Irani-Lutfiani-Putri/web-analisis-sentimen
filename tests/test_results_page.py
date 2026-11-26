import os

import pytest

from app import create_app
from app.extensions import db
from app.models import Comment, Dataset, ModelRun, Prediction, User
from app.services.preprocessing_service import PREPROCESSING_VERSION
from app.services.training_service import create_split, run_evaluation, run_tfidf, run_training


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
            owner = User(full_name='Peneliti', email='results@test.local')
            owner.set_password('secure-password-123')
            db.session.add(owner)
            db.session.flush()
            dataset = Dataset(
                user_id=owner.id, original_filename='hasil.csv',
                stored_filename='hasil-private.csv', file_path='private',
                row_count=36, comment_column='isi', status='processed',
            )
            empty = Dataset(
                user_id=owner.id, original_filename='belum-hasil.csv',
                stored_filename='belum-hasil-private.csv', file_path='private',
                row_count=0, comment_column='isi', status='validated',
            )
            db.session.add_all([dataset, empty])
            db.session.flush()

            row_number = 2
            for label in ('Negatif', 'Netral', 'Positif'):
                for index in range(12):
                    db.session.add(Comment(
                        dataset_id=dataset.id, row_number=row_number,
                        comment_text=f'{label} tambang {index}',
                        cleaned_text=f'{label.lower()} tambang {index}',
                        preprocessing_version=PREPROCESSING_VERSION,
                        sentiment_label=label, label_source='lexicon',
                    ))
                    row_number += 1
            db.session.commit()

            run = create_split(dataset.id, owner.id, '70:30')
            run_tfidf(run, app.config['MODEL_FOLDER'])
            run_training(run, app.config['MODEL_FOLDER'])
            run_evaluation(run, app.config['MODEL_FOLDER'])
            run_id = run.id
            empty_id = empty.id
            owner_id = owner.id
            dataset_id = dataset.id
            db.session.remove()
            yield app, owner_id, dataset_id, empty_id, run_id
        finally:
            db.session.remove()
            db.drop_all()


def login(app):
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.post('/login', data={
        'email': 'results@test.local', 'password': 'secure-password-123',
    })
    assert response.status_code == 302
    return client


def test_results_menu_is_between_classification_and_testing(records):
    app, owner_id, dataset_id, empty_id, run_id = records
    client = login(app)
    html = client.get('/results').data.decode()
    assert 'href="/results"' in html
    assert 'Hasil Klasifikasi' in html
    assert 'class="sidebar-link-icon"' not in html
    positions = [
        html.index('href="/dashboard"'),
        html.index('href="/preprocessing"'),
        html.index('href="/classification"'),
        html.index('href="/results"'),
        html.index('href="/testing"'),
    ]
    assert positions == sorted(positions)


def test_results_page_reads_stored_evaluation(records):
    app, owner_id, dataset_id, empty_id, run_id = records
    client = login(app)
    with app.app_context():
        run = db.session.get(ModelRun, run_id)
        first = db.session.execute(
            db.select(Prediction, Comment)
            .join(Comment, Prediction.comment_id == Comment.id)
            .filter(Prediction.model_run_id == run_id, Prediction.source == 'evaluation')
            .order_by(Prediction.row_number, Prediction.id)
        ).first()
        test_count = run.test_count
        accuracy = f'{float(run.accuracy):.4f}'
        f1 = f'{float(run.f1_macro):.4f}'
        report_negatif = f"{float(run.classification_report['Negatif']['precision']):.4f}"
        report_positif = f"{float(run.classification_report['Positif']['precision']):.4f}"
        prediction = first[0]
        comment = first[1]

    response = client.get(f'/results?dataset_id={dataset_id}')
    assert response.status_code == 200
    html = response.data.decode()
    assert 'Hasil Klasifikasi SVM' in html
    assert 'hasil.csv' in html
    assert 'Eksperimen' in html
    assert '70:30' in html
    assert PREPROCESSING_VERSION in html
    assert accuracy in html
    assert f1 in html
    assert 'Confusion matrix: baris aktual, kolom prediksi' in html
    assert 'Metrik per kelas pada data testing' in html
    assert report_negatif in html
    assert report_positif in html
    assert 'id="prediction-chart"' in html
    assert f'Menampilkan {test_count} prediksi' in html
    assert f'<td>{comment.comment_text}</td>' in html
    assert f'<td>{comment.cleaned_text}</td>' in html
    assert f'<td>{prediction.actual_label}</td>' in html
    assert f'<td>{prediction.predicted_label}</td>' in html
    expected_status = 'Benar' if prediction.actual_label == prediction.predicted_label else 'Salah'
    assert expected_status in html

    matrix_section = html.split('Confusion matrix: baris aktual, kolom prediksi')[1].split('</table>')[0]
    assert matrix_section.count('<tr>') == 4
    report_section = html.split('Metrik per kelas pada data testing')[1].split('</table>')[0]
    assert report_section.count('<tr>') == 4


def test_results_page_paginates_testing_predictions(records):
    app, owner_id, dataset_id, empty_id, run_id = records
    client = login(app)
    page_one = client.get(f'/results?dataset_id={dataset_id}').data.decode()
    assert 'Halaman 1 dari 2' in page_one
    assert page_one.count('class="prediction-status') == 10
    page_two = client.get(f'/results?dataset_id={dataset_id}&page=2').data.decode()
    assert 'Halaman 2 dari 2' in page_two
    assert page_two.count('class="prediction-status') == 1


def test_results_page_does_not_retrain_or_mix_testing_predictions(records):
    app, owner_id, dataset_id, empty_id, run_id = records
    client = login(app)
    with app.app_context():
        run_count = db.session.scalar(db.select(db.func.count(ModelRun.id)))
        eval_count = db.session.scalar(
            db.select(db.func.count(Prediction.id)).filter_by(model_run_id=run_id, source='evaluation')
        )

    testing = client.post('/testing/single', data={'comment': 'komentar testing terpisah'})
    assert testing.status_code == 200
    page = client.get(f'/results?dataset_id={dataset_id}')
    assert page.status_code == 200
    html = page.data.decode()
    assert 'komentar testing terpisah' not in html
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ModelRun.id))) == run_count
        assert db.session.scalar(
            db.select(db.func.count(Prediction.id)).filter_by(model_run_id=run_id, source='evaluation')
        ) == eval_count
        assert db.session.scalar(
            db.select(db.func.count(Prediction.id)).filter_by(model_run_id=run_id, source='testing')
        ) == 1


def test_results_page_empty_state(records):
    app, owner_id, dataset_id, empty_id, run_id = records
    client = login(app)
    response = client.get(f'/results?dataset_id={empty_id}')
    assert response.status_code == 200
    html = response.data.decode()
    assert 'Belum ada hasil klasifikasi' in html
    assert 'Buka Klasifikasi' in html
    assert 'Accuracy' not in html
