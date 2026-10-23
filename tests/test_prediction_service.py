import io
import pytest
from app.services.prediction_service import predict_single, predict_batch, PredictionError
from app.services.training_service import train_model


def trained_pair():
    suffixes = ('satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan')
    texts = ([f'tambang merusak lingkungan {s}' for s in suffixes] +
             [f'tambang berlangsung biasa {s}' for s in suffixes] +
             [f'tambang memberi manfaat {s}' for s in suffixes])
    labels = ['Negatif'] * 8 + ['Netral'] * 8 + ['Positif'] * 8
    result = train_model(texts, labels, manual_indices={0, 8, 16})
    return result['model'], result['vectorizer']


def test_single_rejects_empty_comment():
    model, vectorizer = trained_pair()
    with pytest.raises(PredictionError, match='kosong'):
        predict_single('  ', model, vectorizer)


def test_single_returns_one_valid_label():
    model, vectorizer = trained_pair()
    assert predict_single('tambang memberi manfaat', model, vectorizer) in {'Negatif', 'Netral', 'Positif'}


def test_batch_counts_valid_and_rejected_rows():
    model, vectorizer = trained_pair()
    csv = io.BytesIO('isi\ntambang memberi manfaat\n" "\ntambang merusak lingkungan\n'.encode())
    result = predict_batch(csv, 'isi', model, vectorizer)
    assert len(result['rows']) == 2
    assert result['rejected'] == 1
    assert sum(result['counts'].values()) == 2


def test_batch_rejects_invalid_encoding_and_column():
    model, vectorizer = trained_pair()
    with pytest.raises(PredictionError, match='UTF-8'):
        predict_batch(io.BytesIO(b'isi\n\xff'), 'isi', model, vectorizer)
    with pytest.raises(PredictionError, match='kolom'):
        predict_batch(io.BytesIO(b'isi\nkomentar'), 'teks', model, vectorizer)
