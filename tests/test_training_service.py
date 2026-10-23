import pytest
from app.services.training_service import train_model, TrainingError


def examples():
    texts = ([f"tambang baik manfaat {i}" for i in range(8)] + [f"tambang buruk rusak {i}" for i in range(8)] + [f"tambang biasa netral {i}" for i in range(8)])
    labels = ["Positif"] * 8 + ["Negatif"] * 8 + ["Netral"] * 8
    return texts, labels


def test_train_splits_before_vectorizer_fit_and_produces_three_class_matrix():
    texts, labels = examples()
    result = train_model(texts, labels, manual_indices={0, 8, 16}, random_state=42)
    assert result['matrix'].shape == (3, 3)
    assert result['class_order'] == ['Negatif', 'Netral', 'Positif']
    assert result['train_size'] + result['test_size'] == len(texts)
    assert result['model'].predict(result['vectorizer'].transform(['tambang baik'])).shape == (1,)


def test_training_rejects_duplicate_text_across_holdout():
    texts, labels = examples()
    texts[1] = texts[0]
    with pytest.raises(TrainingError, match='duplikat'):
        train_model(texts, labels, manual_indices={0, 8, 16})


def test_training_rejects_missing_class():
    texts, labels = examples()
    with pytest.raises(TrainingError, match='tiga kelas'):
        train_model(texts[:16], labels[:16])


def test_training_rejects_too_few_manual_holdout_labels():
    with pytest.raises(TrainingError):
        train_model(['baik', 'buruk', 'biasa'], ['Positif', 'Negatif', 'Netral'], manual_indices={0, 1, 2})
