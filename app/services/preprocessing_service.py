"""One deterministic transformation for training and inference."""
import re
from functools import lru_cache
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

NEGATIONS = {"tidak", "bukan", "belum", "tak", "jangan"}


@lru_cache(maxsize=1)
def _stopwords():
    return set(StopWordRemoverFactory().get_stop_words()) - NEGATIONS


@lru_cache(maxsize=1)
def _stemmer():
    return StemmerFactory().create_stemmer()


def transform_stages(text):
    cleaned = re.sub(r"https?://\S+|www\.\S+|@\w+", " ", text or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    folded = cleaned.lower()
    tokens = re.findall(r"[a-zA-ZÀ-ÿ]+", folded)
    kept = [token for token in tokens if token not in _stopwords()]
    stemmed = " ".join(token if token in NEGATIONS else _stemmer().stem(token) for token in kept)
    return {"cleaning": cleaned.strip(), "case_folding": folded.strip(),
            "stopword": " ".join(kept), "stemming": stemmed}


def preprocess_text(text):
    return transform_stages(text)["stemming"]


def process_dataset(dataset_id, progress=None, chunk_size=100):
    from app.extensions import db
    from app.models import Dataset, Comment
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        raise ValueError("Dataset tidak ditemukan")
    comments = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id)).scalars().all()
    if not comments or any(c.lexicon_processed_at is None for c in comments if c.manual_label is None):
        raise ValueError("Jalankan pelabelan Lexicon sebelum preprocessing")
    total = len(comments)
    if progress:
        progress(0, total)
    for index, comment in enumerate(comments, start=1):
        comment.cleaned_text = preprocess_text(comment.comment_text)
        if progress and (index % chunk_size == 0 or index == total):
            db.session.commit()
            progress(index, total)
    dataset.status = "processed"
    db.session.commit()
    if progress:
        progress(total, total)
    return len(comments)
