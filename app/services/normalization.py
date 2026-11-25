"""Normalization rules for Indonesian informal text.

The dictionary lives in ``app/data/normalization_id.tsv`` so it can be
updated without touching the processing logic. The cache is keyed by the
file's modification time, so editing the TSV is picked up automatically on
the next preprocessing run. Unknown words are kept as-is.
"""
import hashlib
import re
import threading
from pathlib import Path

DICTIONARY_PATH = Path(__file__).resolve().parents[1] / "data" / "normalization_id.tsv"

# Minimal fallback if the external dictionary is unavailable. Keep this small;
# the real source of truth is the TSV file.
_FALLBACK = {
    "knp": "kenapa",
    "gk": "tidak",
    "ga": "tidak",
    "gak": "tidak",
    "hannya": "hanya",
    "tetep": "tetap",
    "baguuuus": "bagus",
    "bgt": "banget",
    "aja": "saja",
}

# Laughter and short particles that must not be mistaken for random noise.
PRESERVE_TOKENS = {
    "wkwk", "wkwkwk", "kwkw", "kwkwkw",
    "haha", "hahaha", "hehe", "hehehe", "hihi", "huhu",
    "cuk", "ngakak",
}

# Keyboard-mash and sentence-fragment patterns. Keep this narrow so
# meaningful words are not lost.
NOISE_TOKENS = {"gkgk", "gkgkgk", "kgkg", "kgkgkg"}
FRAGMENT_TOKENS = {"an", "ny", "ber", "se"}
_RANDOM_PATTERN = re.compile(r"^(?:gk|kg){2,}$")
_RANDOM_CONSONANTS = re.compile(r"^[bcdfghjklmnpqrstvwxyz]{5,}$")
_REPEATED_CHAR = re.compile(r"(.)\1{2,}")

_MAP_LOCK = threading.Lock()
_MAP_STATE = {"mtime": None, "map": {}}


def _read_dictionary():
    mapping = dict(_FALLBACK)
    if not DICTIONARY_PATH.is_file():
        return mapping
    with DICTIONARY_PATH.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            source, target = (part.strip().lower() for part in parts)
            if source and target:
                mapping[source] = target
    return mapping


def normalization_map():
    """Load the dictionary, refreshing it when the TSV file changes."""
    try:
        mtime = DICTIONARY_PATH.stat().st_mtime_ns
    except OSError:
        mtime = None
    with _MAP_LOCK:
        if _MAP_STATE["mtime"] != mtime or not _MAP_STATE["map"]:
            _MAP_STATE["map"] = _read_dictionary()
            _MAP_STATE["mtime"] = mtime
        return _MAP_STATE["map"]


def reload_normalization():
    """Force the next normalization_map() call to read the TSV again."""
    with _MAP_LOCK:
        _MAP_STATE["mtime"] = None
        _MAP_STATE["map"] = {}


def normalization_digest():
    """Short fingerprint used in PREPROCESSING_VERSION."""
    if not DICTIONARY_PATH.is_file():
        return "missing"
    return hashlib.sha256(DICTIONARY_PATH.read_bytes()).hexdigest()[:12]


def is_noise_token(token):
    """True for a keyboard mash, false for meaningful laughter/short words."""
    if not token or token in PRESERVE_TOKENS:
        return False
    if token in NOISE_TOKENS or token in FRAGMENT_TOKENS:
        return True
    if len(token) >= 3 and len(set(token)) == 1:
        return True
    return bool(_RANDOM_PATTERN.fullmatch(token) or _RANDOM_CONSONANTS.fullmatch(token))


def normalize_token(token, mapping=None):
    """Normalize one lowercase token; unknown tokens are preserved."""
    token = (token or "").lower()
    if not token:
        return ""
    # Single letters are leftovers from numbers, punctuation, or initials and
    # carry no sentiment on their own.
    if len(token) == 1:
        return ""
    mapping = mapping or normalization_map()
    if token in mapping:
        return mapping[token]

    # Detect random noise before collapsing repeated letters so aaaaaa does
    # not become a single "a".
    if is_noise_token(token):
        return ""

    # baguuuus -> bagus, bangeeet -> banget. Only runs of 3+ are collapsed so
    # ordinary double letters such as "maaf" and "saat" stay intact.
    collapsed = _REPEATED_CHAR.sub(r"\1", token)
    if collapsed != token:
        if collapsed in mapping:
            return mapping[collapsed]
        token = collapsed

    if is_noise_token(token):
        return ""
    return token
