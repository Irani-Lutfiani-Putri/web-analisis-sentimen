"""One deterministic transformation for training and inference."""
import re
import threading
import unicodedata
from functools import lru_cache
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

from app.services.normalization import (
    normalization_digest,
    normalization_map,
    normalize_token,
    reload_normalization,
)

# Bump the base version when the rules change. The dictionary fingerprint is
# appended automatically so editing the TSV also invalidates old results.
PREPROCESSING_BASE_VERSION = "2026-11-25-v7"


def preprocessing_version():
    return f"{PREPROCESSING_BASE_VERSION}:{normalization_digest()}"


PREPROCESSING_VERSION = preprocessing_version()

NEGATIONS = {"tidak", "bukan", "belum", "tak", "jangan"}

# Words that Sastrawi over-stems or that must remain recognisable.
STEMMING_OVERRIDES = {
    "lingkungan": "lingkungan",
    "lingkungannya": "lingkungan",
    "setuju": "setuju",
    "setujunya": "setuju",
    "kerusakan": "rusak",
    "kerusakannya": "rusak",
    "perusakan": "rusak",
    "pengrusakan": "rusak",
    "pemerintah": "pemerintah",
    "pemerintahnya": "pemerintah",
    "pemerintahan": "pemerintah",
    "pemerintahannya": "pemerintah",
    "pejabat": "pejabat",
    "pejabatnya": "pejabat",
    "tujuan": "tujuan",
    "tujuannya": "tujuan",
    "bertujuan": "tujuan",
    "ditujukan": "tujuan",
    "menuju": "menuju",
    "perampokan": "rampok",
    "perampok": "rampok",
    "menguras": "kuras",
    "uras": "kuras",
    "lainnya": "lain",
    "lainya": "lain",
    "lai": "lain",
    "memilukan": "pilu",
    "belasan": "belas",
    "perjalanan": "perjalanan",
    "perusahaan": "perusahaan",
    "perusahaannya": "perusahaan",
    "freeport": "freeport",
    "grasberg": "grasberg",
    "gresik": "gresik",
    "papua": "papua",
    "timika": "timika",
    "mimika": "mimika",
    "indonesia": "indonesia",
    "tambang": "tambang",
    "emas": "emas",
    "tembaga": "tembaga",
    "nikel": "nikel",
    "tailing": "tailing",
    "smelter": "smelter",
    "amdal": "amdal",
    "telung": "telung",
}

# Keep words that carry sentiment or are needed by the research examples.
PROTECTED_STOPWORDS = NEGATIONS | {
    "kenapa", "hanya", "kalian", "banget", "tetap", "cuk", "amat",
}

# Fillers, English function words, and conjunctions not covered by Sastrawi.
EXTRA_STOPWORDS = {
    "aja", "kalau", "klo", "kalo", "doang", "sih", "deh", "dong", "kok",
    "yah", "ya", "nih", "tuh", "lah", "kah", "pun", "kan", "nya", "rp",
    "nah", "si", "eh", "ah",
    "the", "of", "and", "to", "in", "for", "from", "is", "are", "was",
    "were", "be", "been", "this", "that", "with", "on", "at", "by", "it",
    "its", "or", "as", "you", "my", "me", "we", "they", "up",
}

# Measurement units and quantity words are not sentiment features. They are
# removed even when the number is gone, so "ribuan ton" does not leave
# "ribu ton" behind.
UNIT_TOKENS = {
    "ton", "ons", "meter", "gram", "liter", "hektar", "persen",
    "ribu", "ratus", "puluh", "belas", "juta", "miliar", "triliun",
    "km", "kg", "ml", "mm", "ha", "rb", "jt",
}

# Numeric measurements are treated as one expression: "7m" and "10 ton" are
# removed completely. Standalone units are removed by UNIT_TOKENS, while
# domain words such as "emas" and "tambang" stay. Update this tuple when new
# units appear.
NUMBER_UNITS = (
    "triliun", "miliar", "hektar", "persen", "meter", "gram", "liter",
    "ribu", "juta", "ton", "ons", "km2", "m3", "m2", "km", "cm", "mm",
    "kg", "ml", "rb", "jt", "ha", "k", "m", "g", "l",
)
_NUMBER_UNIT_RE = re.compile(
    r"\b\d[\d.,]*\s*(?:" + "|".join(NUMBER_UNITS) + r")\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"\b\d[\d.,]*\s*%")

# Stylized and lookalike letters from social media text. NFKC handles
# mathematical letters; these three are not converted by NFKC.
_HOMOGLYPHS = str.maketrans({"ɡ": "g", "χ": "x", "ː": ""})

# Locks are per process. The current job runner is also in-process, so this
# prevents duplicate preprocessing clicks from running at the same time.
_active_lock = threading.Lock()
_active_datasets = set()


class DatasetBusyError(ValueError):
    """Raised when preprocessing for the same dataset is already running."""


def is_processing(dataset_id):
    with _active_lock:
        return dataset_id in _active_datasets


def _claim_dataset(dataset_id):
    with _active_lock:
        if dataset_id in _active_datasets:
            raise DatasetBusyError("Preprocessing dataset ini sedang berjalan")
        _active_datasets.add(dataset_id)


def _release_dataset(dataset_id):
    with _active_lock:
        _active_datasets.discard(dataset_id)


@lru_cache(maxsize=1)
def _stopwords():
    base = set(StopWordRemoverFactory().get_stop_words())
    return (base | EXTRA_STOPWORDS | UNIT_TOKENS) - PROTECTED_STOPWORDS


@lru_cache(maxsize=1)
def _stemmer():
    return StemmerFactory().create_stemmer()


def _clean_text(text):
    """Remove URLs, HTML, mentions, numbers, symbols and repeated spaces."""
    cleaned = text or ""
    cleaned = unicodedata.normalize("NFKC", cleaned).translate(_HOMOGLYPHS)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"&[a-zA-Z]+;", " ", cleaned)
    cleaned = re.sub(r"\b(?:https?|ftp)://\S+|www\.\S+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"@\w+", " ", cleaned)
    cleaned = _NUMBER_UNIT_RE.sub(" ", cleaned)
    cleaned = _PERCENT_RE.sub(" ", cleaned)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"[_\d]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _stem(token):
    if token in NEGATIONS:
        return token
    if token in STEMMING_OVERRIDES:
        return STEMMING_OVERRIDES[token]
    return _stemmer().stem(token)


def transform_stages(text, *, stem=True):
    """Return each stage in order.

    Pass ``stem=False`` when the stored final text is already available. The
    comparison table uses this to avoid running Sastrawi on every page load.
    """
    cleaned = _clean_text(text)
    folded = cleaned.lower()

    tokens = re.findall(r"[^\W\d_]+", folded, flags=re.UNICODE)
    mapping = normalization_map()
    normalized_tokens = []
    for token in tokens:
        normalized = normalize_token(token, mapping)
        if normalized:
            normalized_tokens.append(normalized)
    normalized = " ".join(normalized_tokens)

    kept = [token for token in normalized_tokens if token not in _stopwords()]
    stages = {
        "cleaning": cleaned,
        "case_folding": folded,
        "tokenizing": " | ".join(tokens),
        "normalization": normalized,
        "stopword": " ".join(kept),
    }
    if not stem:
        return stages

    # Quantity words such as "ribuan" only become "ribu" after stemming, so
    # filter units again on the final forms.
    stemmed_tokens = []
    for token in kept:
        stem = _stem(token)
        if stem and stem not in UNIT_TOKENS:
            stemmed_tokens.append(stem)
    stages["stemming"] = " ".join(stemmed_tokens)
    return stages


def preprocess_text(text):
    return transform_stages(text)["stemming"]


def process_dataset(dataset_id, progress=None, chunk_size=100):
    """Preprocess rows that are new or use an older preprocessing version.

    Rows already processed with PREPROCESSING_VERSION are skipped, so an
    interrupted job resumes instead of starting from row one.
    """
    from app.extensions import db
    from app.models import Dataset, Comment
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        raise ValueError("Dataset tidak ditemukan")
    comments = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id)).scalars().all()
    if not comments or any(c.lexicon_processed_at is None for c in comments if c.manual_label is None):
        raise ValueError("Jalankan pelabelan Lexicon sebelum preprocessing")

    _claim_dataset(dataset_id)
    try:
        reload_normalization()
        version = preprocessing_version()
        pending = [
            comment for comment in comments
            if comment.cleaned_text is None
            or comment.preprocessing_version != version
        ]
        total = len(pending)
        if progress:
            progress(0, total)
        for index, comment in enumerate(pending, start=1):
            comment.cleaned_text = preprocess_text(comment.comment_text)
            comment.preprocessing_version = version
            if progress and (index % chunk_size == 0 or index == total):
                db.session.commit()
                progress(index, total)
        dataset.status = "processed"
        db.session.commit()
        if progress:
            progress(total, total)
        return total
    finally:
        _release_dataset(dataset_id)
