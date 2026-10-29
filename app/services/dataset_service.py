"""CSV decoding, mapping and row validation, independent of HTTP/database."""
import csv
import io


class DatasetError(ValueError):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


def parse_csv(stream, comment_column, label_column=None):
    try:
        content = stream.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DatasetError("Encoding CSV harus UTF-8", field="file") from exc
    if not content.strip():
        raise DatasetError("CSV kosong", field="file")
    try:
        sample = content[:8192]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(content, newline=""), dialect=dialect, strict=True)
        columns = reader.fieldnames or []
        if not comment_column or comment_column not in columns:
            raise DatasetError("Kolom komentar tidak ditemukan; pilih kolom yang tersedia", field="comment_column")
        if label_column and label_column not in columns:
            raise DatasetError("Kolom label tidak ditemukan", field="label_column")
        rows = []
        rejected = 0
        for row_number, record in enumerate(reader, start=2):
            text = (record.get(comment_column) or "").strip()
            label = (record.get(label_column) or "").strip().capitalize() if label_column else None
            if not text or (label_column and label and label not in {"Positif", "Negatif", "Netral"}):
                rejected += 1
                continue
            rows.append((row_number, text, label or None))
    except csv.Error as exc:
        raise DatasetError("Struktur CSV tidak valid", field="file") from exc
    if not rows:
        raise DatasetError("CSV tidak memiliki baris komentar valid", field="file")
    return rows, {"accepted": len(rows), "rejected": rejected, "columns": columns}
