"""Download the pinned InSet lexicon into storage/lexicon and verify SHA-256.

The dictionary is not committed (storage/ is gitignored) because the upstream
repository states no license; docs/lexicon_source.md records the provenance.

Usage:
    .venv/Scripts/python.exe python_instruct/fetch_lexicon.py
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "storage" / "lexicon"
COMMIT = "9cb9d2971c575d64f4f0ed13c35048095f072a5b"
BASE = f"https://raw.githubusercontent.com/fajri91/InSet/{COMMIT}"
FILES = {
    "positive.tsv": "4d0dc2a6b2fe88a438fe5a61663f45c5cf60ebaeb019d4ca4d31c3315121c2ae",
    "negative.tsv": "b8d4b231077967d07ae07014b9dcea255301c2b17a2452c215e3d810a4ba3be4",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    failures = []
    for name, expected in FILES.items():
        destination = TARGET / name
        if destination.is_file() and sha256(destination) == expected:
            print(f"OK (sudah ada) {destination.relative_to(ROOT)}")
            continue
        print(f"Mengunduh {name}…")
        with urllib.request.urlopen(f"{BASE}/{name}", timeout=60) as response:
            destination.write_bytes(response.read())
        actual = sha256(destination)
        if actual != expected:
            failures.append(f"{name}: SHA-256 {actual} != {expected}")
        else:
            print(f"OK {destination.relative_to(ROOT)}")
    if failures:
        print("\nVerifikasi gagal:")
        for item in failures:
            print(" -", item)
        sys.exit(1)
    print("\nKamus lexicon siap di storage/lexicon. Verifikasi SHA-256 cocok dengan docs/lexicon_source.md.")


if __name__ == "__main__":
    main()
