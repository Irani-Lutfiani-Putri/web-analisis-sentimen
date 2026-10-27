import os
import pytest
from itsdangerous import URLSafeTimedSerializer
from app import create_app
from app.extensions import db
from app.models import User, Dataset, Comment


@pytest.fixture
def setup(monkeypatch):
    if not os.environ.get('TEST_DATABASE_URL'):
        pytest.skip('TEST_DATABASE_URL MySQL terpisah belum tersedia')
    monkeypatch.setenv('DATABASE_URL', os.environ['TEST_DATABASE_URL'])
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app(); app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        users=[]
        for role in ('user','superadmin'):
            u=User(full_name=role, email=f'{role}@test.local', role=role)
            u.set_password('secure-password-123'); db.session.add(u); users.append(u)
        db.session.flush()
        d=Dataset(user_id=users[0].id, original_filename='uji.csv',stored_filename='private-uji.csv',file_path='private',row_count=1,comment_column='isi',status='validated')
        db.session.add(d);db.session.flush()
        c=Comment(dataset_id=d.id,row_number=2,comment_text='tidak buruk',lexicon_score=-3,label_source='review',review_status='review')
        db.session.add(c);db.session.commit()
        dataset_id, comment_id = d.id, c.id
    yield app, dataset_id, comment_id
    with app.app_context():
        db.session.remove();db.drop_all()


def logged_in(app, role):
    client=app.test_client()
    with client.session_transaction() as sess:
        sess['csrf_token']='lexicon-nonce'
    token=URLSafeTimedSerializer(app.secret_key,salt='wtf-csrf-token').dumps('lexicon-nonce')
    response = client.post('/login',data={'email':f'{role}@test.local','password':'secure-password-123','csrf_token':token})
    assert response.status_code==302, response.data.decode()[:200]
    return client,token


def test_user_cannot_get_label_details_or_change_manual_label(setup):
    app,dataset_id,comment_id=setup
    client,token=logged_in(app,'user')
    assert client.get(f'/preprocessing/labels/details?dataset_id={dataset_id}').status_code==403
    assert client.post('/preprocessing/labels/manual',data={'csrf_token':token,'comment_id':comment_id,'label':'Positif'}).status_code==403
    response=client.get('/preprocessing')
    assert response.status_code==200
    for secret in (b'lexicon_score', b'label_source', b'<td>-3</td>', b'/preprocessing/labels/manual'):
        assert secret not in response.data
    assert b'<th>Skor</th>' not in response.data
    assert b'<th>Sumber</th>' not in response.data


def test_admin_can_review_and_history_is_recorded(setup):
    from app.models import LabelHistory
    app,dataset_id,comment_id=setup
    client,token=logged_in(app,'superadmin')
    assert client.get(f'/preprocessing/labels/details?dataset_id={dataset_id}').status_code==404
    response=client.post('/preprocessing/labels/manual',data={'csrf_token':token,'comment_id':comment_id,'label':'Positif'})
    assert response.status_code==404
    with app.app_context():
        assert db.session.get(Comment,comment_id).manual_label is None
        assert db.session.execute(db.select(LabelHistory)).first() is None


def test_admin_can_label_owned_comment(setup):
    from app.models import LabelHistory
    import re as _re
    import time as _time
    app, _, _ = setup
    with app.app_context():
        admin = db.session.execute(db.select(User).filter_by(role='superadmin')).scalar_one()
        d = Dataset(user_id=admin.id, original_filename='admin.csv', stored_filename='admin-private.csv', file_path='private', row_count=1, comment_column='isi', status='validated')
        db.session.add(d); db.session.flush()
        c = Comment(dataset_id=d.id, row_number=2, comment_text='tidak buruk')
        db.session.add(c); db.session.commit()
        dataset_id, comment_id, admin_id = d.id, c.id, admin.id
    with app.app_context():
        assert dataset_id in db.session.execute(db.select(Dataset.id)).scalars().all()
    client, token = logged_in(app, 'superadmin')
    with client.session_transaction() as session:
        assert session.get('_user_id') == str(admin_id)
    with app.app_context():
        assert db.session.get(Dataset, dataset_id).user_id == admin_id
    assert client.get(f'/preprocessing/labels/details?dataset_id={dataset_id}').status_code == 200
    lexicon = client.post('/preprocessing/lexicon/run', data={'csrf_token': token, 'dataset_id': dataset_id})
    assert lexicon.status_code == 302
    # Lexicon runs in a background job; wait for it before asserting results.
    job = _re.search(r'job=([0-9a-f]{32})', lexicon.headers.get('Location', ''))
    assert job, lexicon.headers.get('Location')
    deadline = _time.time() + 60
    status = {}
    while _time.time() < deadline:
        status = client.get(f'/preprocessing/jobs/{job.group(1)}').get_json() or {}
        if status.get('status') in ('completed', 'failed'):
            break
        _time.sleep(0.5)
    assert status.get('status') == 'completed', status
    with app.app_context():
        annotated = db.session.get(Comment, comment_id)
        assert annotated.lexicon_version is not None
        assert annotated.review_status == 'review'
    response = client.post('/preprocessing/labels/manual', data={'csrf_token':token, 'comment_id':comment_id, 'label':'Positif'})
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Comment, comment_id).manual_label == 'Positif'
        assert db.session.execute(db.select(LabelHistory)).scalar_one().new_label == 'Positif'


def test_nonowner_cannot_run_lexicon_on_dataset(setup):
    app,dataset_id,_=setup
    client,token=logged_in(app,'superadmin')
    assert client.post('/preprocessing/lexicon/run',data={'csrf_token':token,'dataset_id':dataset_id}).status_code==404
