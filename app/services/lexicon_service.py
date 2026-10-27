"""Conservative lexicon annotation; uncertainty requires human review."""
import hashlib
import re
import csv
from pathlib import Path

INSET_VERSION = "InSet@9cb9d2971c575d64f4f0ed13c35048095f072a5b"

# SHA-256 of the two InSet files at the commit above; recorded in
# docs/lexicon_source.md. A mismatch means the dictionary is not the one the
# experiments were documented against.
EXPECTED_SHA256 = {
    "positive.tsv": "4d0dc2a6b2fe88a438fe5a61663f45c5cf60ebaeb019d4ca4d31c3315121c2ae",
    "negative.tsv": "b8d4b231077967d07ae07014b9dcea255301c2b17a2452c215e3d810a4ba3be4",
}


class LexiconError(ValueError):
    """Raised when the dictionary is missing, unreadable or not the pinned file."""


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inset(folder):
    """Return a list of problems; empty list means the folder is usable."""
    root = Path(folder)
    if not root.is_dir():
        return [f"Folder kamus tidak ditemukan: {root}"]
    problems = []
    for name, expected in EXPECTED_SHA256.items():
        path = root / name
        if not path.is_file():
            problems.append(f"Berkas {name} tidak ada di {root}")
            continue
        actual = _sha256(path)
        if actual != expected:
            problems.append(f"SHA-256 {name} tidak cocok (dapat {actual[:12]}…)")
    return problems


def load_inset(folder):
    """Load private InSet TSV files; conflicting words are left for review."""
    problems = verify_inset(folder)
    if problems:
        raise LexiconError("; ".join(problems))
    positive = {}
    negative = {}
    for name, target in (("positive.tsv", positive), ("negative.tsv", negative)):
        with (Path(folder) / name).open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                target[row["word"].strip().lower()] = int(row["weight"])
    collisions = set(positive) & set(negative)
    return {**{word: score for word, score in positive.items() if word not in collisions},
            **{word: score for word, score in negative.items() if word not in collisions}}, collisions


NEGATIONS = {"tidak", "bukan", "belum", "tak", "jangan", "ga", "gak", "nggak"}


def classify_comment(text, weights, conflicting_words=()):
    tokens = re.findall(r"\b[\w]+\b", text.lower())
    hits = [weights[token] for token in tokens if token in weights]
    score = sum(hits)
    ambiguous = (any(token in NEGATIONS or token in conflicting_words for token in tokens)
                 or (any(hit > 0 for hit in hits) and any(hit < 0 for hit in hits)))
    if not hits or score == 0 or ambiguous:
        return {"label": None, "score": score, "review": True}
    return {"label": "Positif" if score > 0 else "Negatif", "score": score, "review": False}


def annotate_dataset(dataset_id, weights, version, conflicting_words=(), progress=None, chunk_size=100):
    from datetime import datetime, timezone
    from app.extensions import db
    from app.models import Comment
    if not version:
        raise ValueError("Versi lexicon wajib dicatat")
    comments = db.session.execute(db.select(Comment).filter_by(dataset_id=dataset_id)).scalars().all()
    total = len(comments)
    if progress:
        progress(0, total)
    processed = reviewed = 0
    for index, comment in enumerate(comments, start=1):
        if comment.manual_label:
            if progress and (index % chunk_size == 0 or index == total):
                progress(index, total)
            continue
        result = classify_comment(comment.comment_text, weights, conflicting_words)
        comment.lexicon_label = result["label"]
        comment.lexicon_score = result["score"]
        comment.lexicon_version = version
        comment.lexicon_processed_at = datetime.now(timezone.utc)
        comment.review_status = "review" if result["review"] else "accepted"
        comment.sentiment_label = result["label"]
        comment.label_source = "review" if result["review"] else "lexicon"
        processed += 1
        reviewed += int(result["review"])
        if progress and (index % chunk_size == 0 or index == total):
            db.session.commit()
            progress(index, total)
    db.session.commit()
    if progress:
        progress(total, total)
    return {"processed": processed, "review": reviewed}


def update_manual_label(comment, label, admin_id, note=None):
    from datetime import datetime, timezone
    from app.extensions import db
    from app.models import LabelHistory, User
    if label not in {"Positif", "Negatif", "Netral"}:
        raise ValueError("Label manual tidak valid")
    admin = db.session.get(User, admin_id)
    if not admin or admin.role != "superadmin":
        raise PermissionError("Hanya Superadmin boleh mengubah label manual")
    db.session.add(LabelHistory(comment_id=comment.id, changed_by=admin_id,
                                previous_label=comment.manual_label, new_label=label, note=note))
    comment.manual_label = comment.sentiment_label = label
    comment.label_source = "manual"
    comment.labeled_by = admin_id
    comment.labeled_at = datetime.now(timezone.utc)
    comment.label_note = note
    comment.review_status = "resolved"
    db.session.commit()
