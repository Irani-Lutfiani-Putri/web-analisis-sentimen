from app.services.preprocessing_service import preprocess_text, transform_stages


def test_negation_survives_stopword_and_stemming():
    stages = transform_stages("Tidak merusak, bukan baik, belum selesai!")
    assert "tidak" in stages["stopword"].split()
    assert "bukan" in stages["stopword"].split()
    assert "belum" in stages["stopword"].split()
    assert "tidak" in stages["stemming"].split()
    assert "bukan" in stages["stemming"].split()
    assert "belum" in stages["stemming"].split()
    assert preprocess_text("Tidak merusak, bukan baik, belum selesai!") == stages["stemming"]


def test_empty_text_does_not_produce_fake_tokens():
    assert preprocess_text("  https://example.com  ") == ""


def test_cleaning_then_casefold_are_inspectable():
    stages = transform_stages("Tambang BAGUS! https://example.com @akun")
    assert "http" not in stages["cleaning"].lower()
    assert "@" not in stages["cleaning"]
    assert stages["case_folding"] == stages["case_folding"].lower()
