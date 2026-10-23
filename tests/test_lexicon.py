from app.services.lexicon_service import classify_comment

LEXICON = {"baik": 3, "buruk": -3, "rusak": -4, "manfaat": 3}


def test_clear_polarity():
    result = classify_comment("tambang baik", LEXICON)
    assert result["label"] == "Positif"
    assert result["score"] == 3
    assert result["review"] is False


def test_zero_not_forced_neutral():
    result = classify_comment("tambang berjalan", LEXICON)
    assert result["label"] is None
    assert result["review"] is True


def test_negation_requires_review():
    result = classify_comment("tidak rusak", LEXICON)
    assert result["label"] is None
    assert result["review"] is True


def test_conflicting_lexicon_word_requires_review():
    result = classify_comment('baik', {}, conflicting_words={'baik'})
    assert result['label'] is None
    assert result['review'] is True


def test_mixed_polarity_requires_review():
    result = classify_comment("baik tapi buruk", LEXICON)
    assert result["label"] is None
    assert result["review"] is True
