"""Split before fitting TF-IDF; only independent manual labels may form test set."""
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score, precision_recall_fscore_support
from sklearn.svm import SVC

CLASSES = ['Negatif', 'Netral', 'Positif']


class TrainingError(ValueError):
    pass


def train_model(texts, labels, *, manual_indices=None, random_state=42):
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
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, predicted, labels=CLASSES, average='macro', zero_division=0)
    return {'model': model, 'vectorizer': vectorizer, 'matrix': matrix,
            'class_order': CLASSES, 'train_size': len(train_ids), 'test_size': len(test_ids),
            'accuracy': accuracy_score(y_test, predicted), 'precision_macro': precision,
            'recall_macro': recall, 'f1_macro': f1,
            'report': classification_report(y_test, predicted, labels=CLASSES, output_dict=True, zero_division=0),
            'test_ids': test_ids, 'train_ids': train_ids, 'random_state': random_state}


def train_dataset(dataset_id, owner_id, storage):
    """Train only with a disjoint, independently manually labeled test partition."""
    from pathlib import Path
    import joblib
    from app.extensions import db
    from app.models import Dataset, Comment, ModelRun
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset or dataset.user_id != owner_id or dataset.status != 'processed':
        raise TrainingError('Dataset milik pengguna belum selesai preprocessing')
    comments = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id).order_by(Comment.id)).scalars().all()
    eligible = [c for c in comments if c.cleaned_text and c.sentiment_label in CLASSES and c.review_status != 'review']
    manual = {i for i, c in enumerate(eligible) if c.is_independent_holdout and c.manual_label == c.sentiment_label and c.label_source == 'manual'}
    if not manual:
        raise TrainingError('Data uji manual independen belum tersedia')
    result = train_model([c.cleaned_text for c in eligible], [c.sentiment_label for c in eligible], manual_indices=manual)
    run = ModelRun(user_id=owner_id, dataset_id=dataset_id, experiment_name='SVM linear',
                   split_ratio=f'{result["train_size"]}:{result["test_size"]}', random_state=result['random_state'],
                   vectorizer_config={'type': 'TfidfVectorizer'}, svm_config={'kernel': 'linear', 'C': 1.0},
                   accuracy=result['accuracy'], precision_macro=result['precision_macro'],
                   recall_macro=result['recall_macro'], f1_macro=result['f1_macro'],
                   classification_report=result['report'], confusion_matrix=result['matrix'].tolist(), status='running')
    db.session.add(run)
    db.session.flush()
    folder = Path(storage).resolve() / str(run.id)
    folder.mkdir(parents=True, exist_ok=True)
    model_path, vectorizer_path = folder / 'model.joblib', folder / 'vectorizer.joblib'
    try:
        joblib.dump(result['model'], model_path)
        joblib.dump(result['vectorizer'], vectorizer_path)
        run.model_path, run.vectorizer_path = str(model_path), str(vectorizer_path)
        run.status = 'completed'
        db.session.commit()
    except Exception:
        db.session.rollback()
        model_path.unlink(missing_ok=True)
        vectorizer_path.unlink(missing_ok=True)
        raise
    return run


def load_run(run, storage):
    """Only load artifacts from an owned completed experiment; joblib files must be trusted."""
    from pathlib import Path
    import joblib
    if run.status != 'completed' or not run.model_path or not run.vectorizer_path:
        raise TrainingError('Model belum tersedia')
    root = Path(storage).resolve() / str(run.id)
    model_path, vectorizer_path = Path(run.model_path).resolve(), Path(run.vectorizer_path).resolve()
    if model_path != root / 'model.joblib' or vectorizer_path != root / 'vectorizer.joblib':
        raise TrainingError('Pasangan artefak tidak cocok dengan eksperimen')
    if not model_path.is_file() or not vectorizer_path.is_file():
        raise TrainingError('Berkas model atau vectorizer tidak tersedia')
    return joblib.load(model_path), joblib.load(vectorizer_path)
