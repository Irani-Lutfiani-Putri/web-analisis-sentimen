import os
from datetime import datetime, timezone
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Dataset, Comment
from app.services.preprocessing_service import process_dataset


def test_process_dataset_preserves_original_and_stores_cleaned(monkeypatch):
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('MySQL test database required')
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    with app.app_context():
        db.create_all()
        try:
            user = User(full_name='Peneliti', email='process@test.local', role='user')
            user.set_password('secure-password-123')
            db.session.add(user); db.session.flush()
            dataset = Dataset(user_id=user.id, original_filename='uji.csv', stored_filename='process.csv', file_path='private', row_count=1, comment_column='isi', status='validated')
            db.session.add(dataset); db.session.flush()
            comment = Comment(dataset_id=dataset.id, row_number=2, comment_text='Tidak merusak tambang', sentiment_label='Positif', lexicon_label='Positif', label_source='lexicon', lexicon_version='test-v1', lexicon_processed_at=datetime.now(timezone.utc), review_status='accepted')
            db.session.add(comment); db.session.commit()
            assert process_dataset(dataset.id) == 1
            db.session.refresh(comment)
            assert comment.comment_text == 'Tidak merusak tambang'
            assert 'tidak' in comment.cleaned_text.split()
            assert dataset.status == 'processed'
            app.config['WTF_CSRF_ENABLED'] = False
            client = app.test_client()
            assert client.post('/login', data={
                'email': 'process@test.local',
                'password': 'secure-password-123',
            }).status_code == 302
            page = client.get(f'/preprocessing?dataset_id={dataset.id}')
            assert page.status_code == 200
            assert b'preprocessing-stages' in page.data
            assert page.data.count(b'class="stage-icon"') == 4
            assert b'<th>Label</th>' in page.data
            assert b'Positif' in page.data
        finally:
            db.session.remove(); db.drop_all()
