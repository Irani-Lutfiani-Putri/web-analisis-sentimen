import os
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Dataset, Comment
from app.services.training_service import train_dataset, TrainingError


def test_imported_labels_are_not_independent_holdout(monkeypatch, tmp_path):
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL MySQL terpisah belum tersedia')
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    with app.app_context():
        db.create_all()
        try:
            admin = User(full_name='Admin', email='eligibility@test.local', role='superadmin')
            admin.set_password('secure-password-123')
            db.session.add(admin); db.session.flush()
            d = Dataset(user_id=admin.id, original_filename='uji.csv', stored_filename='eligibility.csv', file_path='private', row_count=6, comment_column='isi', status='processed')
            db.session.add(d); db.session.flush()
            for group, label in enumerate(('Negatif', 'Netral', 'Positif')):
                for n in range(2):
                    db.session.add(Comment(dataset_id=d.id, row_number=group*2+n+2, comment_text=f'{label} tambang {n}', cleaned_text=f'{label.lower()} tambang {n}', manual_label=label if n==0 else None, sentiment_label=label, label_source='manual' if n==0 else 'lexicon', labeled_by=admin.id if n==0 else None))
            db.session.commit()
            with pytest.raises(TrainingError, match='independen'):
                train_dataset(d.id, admin.id, str(tmp_path))
        finally:
            db.session.remove(); db.drop_all()
