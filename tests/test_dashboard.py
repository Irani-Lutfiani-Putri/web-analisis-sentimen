import os
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Dataset, Comment


def test_dashboard_reads_owned_dataset_and_actual_count(monkeypatch):
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL MySQL terpisah belum tersedia')
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        try:
            owner = User(full_name='Peneliti', email='dashboard@test.local', role='user')
            owner.set_password('secure-password-123')
            db.session.add(owner); db.session.flush()
            dataset = Dataset(user_id=owner.id, original_filename='pertambangan.csv', stored_filename='dash-private.csv', file_path='private', row_count=1, comment_column='isi', status='validated')
            db.session.add(dataset); db.session.flush()
            db.session.add(Comment(dataset_id=dataset.id, row_number=2, comment_text='Komentar pertambangan'))
            db.session.commit()
            client = app.test_client()
            assert client.post('/login', data={'email':owner.email,'password':'secure-password-123'}).status_code == 302
            response = client.get('/dashboard')
            assert response.status_code == 200
            assert b'pertambangan.csv' in response.data
            assert b'1 komentar' in response.data
            assert b'Belum ada dataset aktif' not in response.data
        finally:
            db.session.remove(); db.drop_all()
