"""Inference with same preprocessing and vectorizer as training."""
import csv
import io
from app.services.preprocessing_service import preprocess_text
from app.services.training_service import CLASSES


class PredictionError(ValueError):
    pass


def predict_single(text, model, vectorizer):
    if not text or not text.strip():
        raise PredictionError('Komentar kosong')
    cleaned = preprocess_text(text)
    if not cleaned:
        raise PredictionError('Komentar kosong setelah preprocessing')
    return str(model.predict(vectorizer.transform([cleaned]))[0])


def predict_batch(stream, comment_column, model, vectorizer):
    try:
        decoded = stream.read().decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise PredictionError('CSV harus UTF-8') from exc
    try:
        reader = csv.DictReader(io.StringIO(decoded, newline=''), strict=True)
        if not reader.fieldnames or not comment_column or comment_column not in reader.fieldnames:
            raise PredictionError('Pilih kolom komentar yang tersedia')
        rows, rejected = [], 0
        counts = {label: 0 for label in CLASSES}
        for row_number, record in enumerate(reader, start=2):
            text = (record.get(comment_column) or '').strip()
            try:
                label = predict_single(text, model, vectorizer)
            except PredictionError:
                rejected += 1
                continue
            rows.append({'row_number': row_number, 'text': text, 'predicted_label': label})
            counts[label] += 1
    except csv.Error as exc:
        raise PredictionError('Struktur CSV tidak valid') from exc
    return {'rows': rows, 'rejected': rejected, 'counts': counts}
