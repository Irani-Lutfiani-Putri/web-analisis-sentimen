"""Split, TF-IDF, SVM training, and evaluation as separate persisted stages."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from app.extensions import db
from app.models import Comment, Dataset, ModelRun, Prediction
from app.services.preprocessing_service import PREPROCESSING_VERSION

CLASSES = ['Negatif', 'Netral', 'Positif']
RATIOS = {'70:30': 0.30, '80:20': 0.20, '90:10': 0.10}
RANDOM_STATE = 42


class TrainingError(ValueError):
    pass


def _now():
    return datetime.now(timezone.utc)


def train_model(texts, labels, *, manual_indices=None, random_state=42):
    """Legacy one-shot helper kept for prediction unit tests."""
    if len(texts) != len(labels) or not texts or set(labels) != set(CLASSES):
        raise TrainingError('Data training harus memiliki tiga kelas valid')
    if manual_indices is None:
        raise TrainingError('Data uji berlabel manual independen wajib disediakan')
    manual_indices = set(manual_indices)
    if any(not isinstance(i, int) or i < 0 or i >= len(texts) for i in manual_indices):
        raise TrainingError('Indeks label manual tidak valid')
    manual_labels = Counter(labels[i] for i in manual_indices)
    if any(manual_labels[c] < 1 for c in CLASSES):
        raise TrainingError('Data uji manual belum mencakup tiga kelas')
    test_ids = sorted(manual_indices)
    train_ids = [i for i in range(len(texts)) if i not in manual_indices]
    if not train_ids or set(labels[i] for i in train_ids) != set(CLASSES):
        raise TrainingError('Data training belum mencakup tiga kelas setelah holdout manual')
    train_texts = [texts[i] for i in train_ids]
    test_texts = [texts[i] for i in test_ids]
    if {text.strip().casefold() for text in train_texts} & {text.strip().casefold() for text in test_texts}:
        raise TrainingError('Teks duplikat antara data training dan data uji manual')
    if len({text.strip().casefold() for text in test_texts}) != len(test_texts):
        raise TrainingError('Teks duplikat dalam data uji manual')
    if len({text.strip().casefold() for text in train_texts}) != len(train_texts):
        raise TrainingError('Teks duplikat dalam data training')

    y_train = [labels[i] for i in train_ids]
    y_test = [labels[i] for i in test_ids]
    try:
        vectorizer = TfidfVectorizer()
        x_train = vectorizer.fit_transform(train_texts)
        x_test = vectorizer.transform(test_texts)
        model = SVC(kernel='linear', C=1.0)
        model.fit(x_train, y_train)
        predicted = model.predict(x_test)
    except ValueError as exc:
        raise TrainingError('Teks atau kelas tidak cukup untuk pelatihan SVM') from exc
    matrix = confusion_matrix(y_test, predicted, labels=CLASSES)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predicted, labels=CLASSES, average='macro', zero_division=0,
    )
    return {
        'model': model, 'vectorizer': vectorizer, 'matrix': matrix,
        'class_order': CLASSES, 'train_size': len(train_ids), 'test_size': len(test_ids),
        'accuracy': accuracy_score(y_test, predicted), 'precision_macro': precision,
        'recall_macro': recall, 'f1_macro': f1,
        'report': classification_report(
            y_test, predicted, labels=CLASSES, output_dict=True, zero_division=0,
        ),
        'test_ids': test_ids, 'train_ids': train_ids, 'random_state': random_state,
    }


def _dataset(dataset_id, owner_id):
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset or dataset.user_id != owner_id:
        raise TrainingError('Dataset tidak ditemukan')
    if dataset.status != 'processed':
        raise TrainingError('Dataset belum selesai preprocessing')
    return dataset


def _eligible_comments(dataset_id):
    rows = db.session.execute(
        db.select(Comment).filter_by(dataset_id=dataset_id).order_by(Comment.id)
    ).scalars().all()
    candidates = [
        comment for comment in rows
        if comment.cleaned_text and comment.cleaned_text.strip()
        and comment.sentiment_label in CLASSES
        and comment.review_status != 'review'
    ]
    raw = [comment for comment in candidates if comment.preprocessing_version == PREPROCESSING_VERSION]
    stale = len(candidates) - len(raw)

    by_text = {}
    duplicates = 0
    conflicts = set()
    for comment in raw:
        key = comment.cleaned_text.strip().casefold()
        if key in by_text:
            duplicates += 1
            if by_text[key].sentiment_label != comment.sentiment_label:
                conflicts.add(key)
            continue
        by_text[key] = comment

    unique = [comment for key, comment in by_text.items() if key not in conflicts]
    counts = Counter(comment.sentiment_label for comment in unique)
    distribution = {label: int(counts.get(label, 0)) for label in CLASSES}
    missing = [label for label in CLASSES if distribution[label] == 0]
    active_classes = [label for label in CLASSES if distribution[label] >= 2]
    low_classes = [label for label in CLASSES if distribution[label] == 1]
    if len(active_classes) < 2:
        if stale:
            message = 'Sebagian komentar belum memakai versi preprocessing terbaru. Jalankan preprocessing ulang.'
        else:
            message = 'Dataset memerlukan minimal dua kelas dengan masing-masing minimal 2 komentar unik.'
    elif low_classes:
        message = 'Kelas ' + ', '.join(low_classes) + ' hanya memiliki 1 komentar unik. Minimal 2 komentar per kelas.'
    else:
        message = ''
    warning = ''
    if not message and missing:
        warning = (
            'Kelas ' + ', '.join(missing)
            + ' belum memiliki label final. Model akan dilatih dengan kelas: '
            + ', '.join(active_classes) + '.'
        )
    return unique, {
        'raw': len(raw),
        'unique': len(unique),
        'duplicates': duplicates,
        'conflicts': len(conflicts),
        'counts': distribution,
        'missing': missing,
        'active_classes': active_classes,
        'ready': not message,
        'message': message,
        'warning': warning,
        'stale': stale,
    }


def dataset_eligibility(dataset_id):
    _, info = _eligible_comments(dataset_id)
    return info


def _distribution(comments):
    counts = Counter(comment.sentiment_label for comment in comments)
    return {label: int(counts.get(label, 0)) for label in CLASSES}


def create_split(dataset_id, owner_id, ratio):
    """Create a persistent stratified split from final, non-review labels."""
    fraction = RATIOS.get(ratio)
    if fraction is None:
        raise TrainingError('Rasio split tidak valid')
    _dataset(dataset_id, owner_id)
    unique, info = _eligible_comments(dataset_id)
    if not info['ready']:
        raise TrainingError(info['message'])

    labels = [comment.sentiment_label for comment in unique]
    positions = list(range(len(unique)))
    try:
        train_positions, test_positions = train_test_split(
            positions,
            test_size=fraction,
            random_state=RANDOM_STATE,
            stratify=labels,
        )
    except ValueError as exc:
        raise TrainingError('Data belum memenuhi syarat stratified split') from exc

    train_comments = [unique[index] for index in train_positions]
    test_comments = [unique[index] for index in test_positions]
    train_distribution = _distribution(train_comments)
    test_distribution = _distribution(test_comments)
    if any(
        train_distribution[label] == 0 or test_distribution[label] == 0
        for label in info['active_classes']
    ):
        raise TrainingError('Split belum menghasilkan semua kelas aktif pada data training dan testing')

    train_texts = {comment.cleaned_text.strip().casefold() for comment in train_comments}
    test_texts = {comment.cleaned_text.strip().casefold() for comment in test_comments}
    if train_texts & test_texts:
        raise TrainingError('Teks yang sama muncul pada data training dan testing')

    run = ModelRun(
        user_id=owner_id,
        dataset_id=dataset_id,
        experiment_name='SVM linear',
        split_ratio=ratio,
        random_state=RANDOM_STATE,
        split_config={
            'ratio': ratio,
            'test_size': fraction,
            'random_state': RANDOM_STATE,
            'stratified': True,
            'classes': info['active_classes'],
            'missing_classes': info['missing'],
            'preprocessing_version': PREPROCESSING_VERSION,
            'raw_rows': info['raw'],
            'unique_rows': info['unique'],
            'duplicates': info['duplicates'],
            'conflicts': info['conflicts'],
        },
        split_indices={
            'train': [int(comment.id) for comment in train_comments],
            'test': [int(comment.id) for comment in test_comments],
        },
        train_size=len(train_comments),
        test_size=len(test_comments),
        train_distribution=train_distribution,
        test_distribution=test_distribution,
        vectorizer_config={'type': 'TfidfVectorizer'},
        svm_config={'kernel': 'linear', 'C': 1.0},
        split_at=_now(),
        status='split',
    )
    db.session.add(run)
    db.session.commit()
    return run


def active_run(dataset_id, owner_id):
    return db.session.execute(
        db.select(ModelRun).filter(
            ModelRun.dataset_id == dataset_id,
            ModelRun.user_id == owner_id,
            ModelRun.split_at.is_not(None),
        ).order_by(ModelRun.id.desc())
    ).scalars().first()


def _run_folder(run, storage):
    folder = Path(storage).resolve() / str(run.id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _load_split_comments(run):
    indices = run.split_indices or {}
    train_ids = [int(value) for value in indices.get('train', [])]
    test_ids = [int(value) for value in indices.get('test', [])]
    if not train_ids or not test_ids:
        raise TrainingError('Split Data belum tersedia')
    if set(train_ids) & set(test_ids):
        raise TrainingError('Data training dan testing tidak boleh beririsan')

    rows = db.session.execute(
        db.select(Comment).filter(Comment.id.in_(train_ids + test_ids))
    ).scalars().all()
    by_id = {int(comment.id): comment for comment in rows}
    if len(by_id) != len(set(train_ids + test_ids)):
        raise TrainingError('Sebagian komentar pada split tidak ditemukan')

    def valid(comment):
        return (
            comment.dataset_id == run.dataset_id
            and comment.cleaned_text and comment.cleaned_text.strip()
            and comment.sentiment_label in CLASSES
            and comment.review_status != 'review'
            and comment.preprocessing_version == PREPROCESSING_VERSION
        )

    train_comments = [by_id[comment_id] for comment_id in train_ids]
    test_comments = [by_id[comment_id] for comment_id in test_ids]
    if not all(valid(comment) for comment in train_comments + test_comments):
        raise TrainingError('Data split tidak lagi memenuhi syarat preprocessing dan label final')
    if {c.cleaned_text.strip().casefold() for c in train_comments} & {
        c.cleaned_text.strip().casefold() for c in test_comments
    }:
        raise TrainingError('Teks yang sama muncul pada data training dan testing')
    return train_comments, test_comments


def run_tfidf(run, storage):
    """Fit TF-IDF on training rows only, then transform the test rows."""
    if not run.split_at:
        raise TrainingError('Split Data belum dijalankan')
    if run.tfidf_at:
        raise TrainingError('TF-IDF sudah dijalankan untuk pipeline ini')
    train_comments, test_comments = _load_split_comments(run)
    try:
        vectorizer = TfidfVectorizer()
        x_train = vectorizer.fit_transform(
            [comment.cleaned_text for comment in train_comments]
        )
        x_test = vectorizer.transform(
            [comment.cleaned_text for comment in test_comments]
        )
    except ValueError as exc:
        raise TrainingError('Teks training belum cukup untuk membentuk vocabulary TF-IDF') from exc

    folder = _run_folder(run, storage)
    vectorizer_path = folder / 'vectorizer.joblib'
    joblib.dump(vectorizer, vectorizer_path)
    sparse.save_npz(folder / 'train_matrix.npz', x_train)
    sparse.save_npz(folder / 'test_matrix.npz', x_test)
    (folder / 'train_labels.json').write_text(
        json.dumps([comment.sentiment_label for comment in train_comments]),
        encoding='utf-8',
    )
    (folder / 'test_labels.json').write_text(
        json.dumps([comment.sentiment_label for comment in test_comments]),
        encoding='utf-8',
    )

    run.vectorizer_path = str(vectorizer_path)
    run.tfidf_vocabulary_size = len(vectorizer.vocabulary_)
    run.tfidf_train_shape = [int(value) for value in x_train.shape]
    run.tfidf_test_shape = [int(value) for value in x_test.shape]
    run.tfidf_at = _now()
    run.status = 'tfidf'
    db.session.commit()
    return run


def run_training(run, storage):
    """Fit SVM with the saved training matrix; no test data is touched."""
    if not run.tfidf_at:
        raise TrainingError('TF-IDF belum dijalankan')
    if run.trained_at:
        raise TrainingError('Training sudah dijalankan untuk pipeline ini')
    folder = _run_folder(run, storage)
    x_train = sparse.load_npz(folder / 'train_matrix.npz')
    y_train = json.loads((folder / 'train_labels.json').read_text(encoding='utf-8'))
    try:
        model = SVC(kernel='linear', C=1.0)
        model.fit(x_train, y_train)
    except ValueError as exc:
        raise TrainingError('Matriks training tidak cukup untuk melatih SVM') from exc
    model_path = folder / 'model.joblib'
    joblib.dump(model, model_path)
    run.model_path = str(model_path)
    run.svm_config = {'kernel': 'linear', 'C': 1.0}
    run.trained_at = _now()
    run.status = 'trained'
    db.session.commit()
    return run


def run_evaluation(run, storage):
    """Evaluate only on the saved test matrix and actual test labels."""
    if not run.trained_at:
        raise TrainingError('Training SVM belum dijalankan')
    if run.evaluated_at:
        raise TrainingError('Evaluasi sudah dijalankan untuk pipeline ini')
    folder = _run_folder(run, storage)
    x_test = sparse.load_npz(folder / 'test_matrix.npz')
    y_test = json.loads((folder / 'test_labels.json').read_text(encoding='utf-8'))
    if not Path(run.model_path or '').is_file():
        raise TrainingError('Model tersimpan tidak ditemukan')
    model = joblib.load(run.model_path)
    predicted = model.predict(x_test)
    _, test_comments = _load_split_comments(run)
    if len(test_comments) != len(y_test) or len(predicted) != len(y_test):
        raise TrainingError('Jumlah prediksi tidak cocok dengan data testing tersimpan')
    classes = run.split_config.get('classes', CLASSES) if run.split_config else CLASSES
    matrix = confusion_matrix(y_test, predicted, labels=classes)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predicted, labels=classes, average='macro', zero_division=0,
    )
    report = classification_report(
        y_test, predicted, labels=classes, output_dict=True, zero_division=0,
    )
    prediction_distribution = {
        label: int((predicted == label).sum()) for label in classes
    }
    db.session.execute(
        db.delete(Prediction).filter_by(model_run_id=run.id, source='evaluation')
    )
    for comment, label in zip(test_comments, predicted):
        db.session.add(Prediction(
            user_id=run.user_id,
            model_run_id=run.id,
            comment_id=comment.id,
            source='evaluation',
            input_text=comment.comment_text,
            actual_label=comment.sentiment_label,
            predicted_label=str(label),
            row_number=comment.row_number,
        ))
    run.accuracy = float(accuracy_score(y_test, predicted))
    run.precision_macro = float(precision)
    run.recall_macro = float(recall)
    run.f1_macro = float(f1)
    run.classification_report = report
    run.confusion_matrix = matrix.tolist()
    run.prediction_distribution = prediction_distribution
    run.test_count = len(y_test)
    run.evaluated_at = _now()
    run.status = 'completed'
    db.session.commit()
    return run


def load_run(run, storage):
    """Load a trained model and its matching vectorizer from an owned experiment."""
    if run.status not in ('trained', 'completed') or not run.model_path or not run.vectorizer_path:
        raise TrainingError('Model belum tersedia')
    root = Path(storage).resolve() / str(run.id)
    model_path, vectorizer_path = Path(run.model_path).resolve(), Path(run.vectorizer_path).resolve()
    if model_path != root / 'model.joblib' or vectorizer_path != root / 'vectorizer.joblib':
        raise TrainingError('Pasangan artefak tidak cocok dengan eksperimen')
    if not model_path.is_file() or not vectorizer_path.is_file():
        raise TrainingError('Berkas model atau vectorizer tidak tersedia')
    return joblib.load(model_path), joblib.load(vectorizer_path)
