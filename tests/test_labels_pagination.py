import os
import pytest
from itsdangerous import URLSafeTimedSerializer
from app import create_app
from app.extensions import db
from app.models import User, Dataset, Comment


@pytest.fixture
def paged(monkeypatch):
    if not os.environ.get('TEST_DATABASE_URL'):
        pytest.skip('TEST_DATABASE_URL MySQL terpisah belum tersedia')
    monkeypatch.setenv('DATABASE_URL', os.environ['TEST_DATABASE_URL'])
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app(); app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        admin = User(full_name='Pengelola', email='pager@test.local')
        admin.set_password('secure-password-123'); db.session.add(admin); db.session.flush()
        dataset = Dataset(user_id=admin.id, original_filename='pager.csv', stored_filename='pager-private.csv',
                          file_path='private', row_count=30, comment_column='isi', status='validated')
        db.session.add(dataset); db.session.flush()
        for n in range(30):
            text = 'tambang merusak sungai' if n % 3 == 0 else ('tambang memberi manfaat' if n % 3 == 1 else 'tambang biasa saja')
            db.session.add(Comment(dataset_id=dataset.id, row_number=n + 2, comment_text=f'{text} nomor {n}',
                                   sentiment_label='Negatif' if n % 3 == 0 else ('Positif' if n % 3 == 1 else 'Netral'),
                                   review_status='review' if n % 5 == 0 else 'accepted',
                                   lexicon_score=n))
        db.session.commit()
        yield app, dataset.id
        db.session.remove(); db.drop_all()


def login(app, token='page-nonce'):
    client = app.test_client()
    with client.session_transaction() as session:
        session['csrf_token'] = token
    csrf = URLSafeTimedSerializer(app.secret_key, salt='wtf-csrf-token').dumps(token)
    assert client.post('/login', data={'email': 'pager@test.local', 'password': 'secure-password-123', 'csrf_token': csrf}).status_code == 302
    return client, csrf


def test_first_page_shows_10_of_30(paged):
    app, dataset_id = paged
    client, _ = login(app)
    html = client.get(f'/labels?dataset_id={dataset_id}&label=semua').data
    assert b'Halaman 1 / 3' in html
    assert b'30 komentar cocok' in html
    assert b'nomor 0' in html


def test_third_page_has_remaining_rows(paged):
    app, dataset_id = paged
    client, _ = login(app)
    page3 = client.get(f'/labels?dataset_id={dataset_id}&label=semua&page=3')
    assert page3.status_code == 200
    assert b'nomor 29' in page3.data
    assert b'nomor 0' not in page3.data


def test_search_filters_rows(paged):
    app, dataset_id = paged
    client, _ = login(app)
    html = client.get(f'/labels?dataset_id={dataset_id}&label=semua&q=merusak').data
    assert b'merusak' in html
    assert b'memberi manfaat' not in html


def test_review_filter_shows_review_rows(paged):
    app, dataset_id = paged
    client, _ = login(app)
    html = client.get(f'/labels?dataset_id={dataset_id}&label=review').data
    assert b'6 komentar cocok' in html
    assert b'nomor 0</td>' in html
    assert b'nomor 1</td>' not in html
