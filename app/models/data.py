"""Relational records for datasets, labels, experiments, and predictions."""
from datetime import datetime, timezone
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class Dataset(db.Model):
    __tablename__ = "datasets"
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    row_count = db.Column(db.Integer, nullable=False, default=0)
    comment_column = db.Column(db.String(100), nullable=False)
    label_column = db.Column(db.String(100))
    dataset_type = db.Column(db.Enum("train", "test", "unassigned"), nullable=False, default="unassigned")
    status = db.Column(db.String(30), nullable=False, default="uploaded")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class Comment(db.Model):
    __tablename__ = "comments"
    __table_args__ = (db.UniqueConstraint("dataset_id", "row_number", name="uq_comment_dataset_row"),)
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    dataset_id = db.Column(db.BigInteger, db.ForeignKey("datasets.id"), nullable=False, index=True)
    row_number = db.Column(db.Integer, nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    cleaned_text = db.Column(db.Text)
    manual_label = db.Column(db.Enum("Positif", "Negatif", "Netral"))
    is_independent_holdout = db.Column(db.Boolean, nullable=False, default=False)
    lexicon_label = db.Column(db.Enum("Positif", "Negatif", "Netral"))
    lexicon_score = db.Column(db.Numeric(10, 6))
    lexicon_version = db.Column(db.String(100))
    lexicon_processed_at = db.Column(db.DateTime)
    review_status = db.Column(db.String(30))
    sentiment_label = db.Column(db.Enum("Positif", "Negatif", "Netral"))
    label_source = db.Column(db.Enum("manual", "lexicon", "review"))
    labeled_by = db.Column(db.BigInteger, db.ForeignKey("users.id"))
    labeled_at = db.Column(db.DateTime)
    label_note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class LabelHistory(db.Model):
    __tablename__ = "label_history"
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    comment_id = db.Column(db.BigInteger, db.ForeignKey("comments.id"), nullable=False, index=True)
    changed_by = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    previous_label = db.Column(db.Enum("Positif", "Negatif", "Netral"))
    new_label = db.Column(db.Enum("Positif", "Negatif", "Netral"), nullable=False)
    note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class ModelRun(db.Model):
    __tablename__ = "model_runs"
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False, index=True)
    dataset_id = db.Column(db.BigInteger, db.ForeignKey("datasets.id"), nullable=False)
    experiment_name = db.Column(db.String(150), nullable=False)
    split_ratio = db.Column(db.String(20), nullable=False)
    random_state = db.Column(db.Integer, nullable=False)
    vectorizer_config = db.Column(db.JSON)
    svm_config = db.Column(db.JSON)
    accuracy = db.Column(db.Numeric(8, 6))
    precision_macro = db.Column(db.Numeric(8, 6))
    recall_macro = db.Column(db.Numeric(8, 6))
    f1_macro = db.Column(db.Numeric(8, 6))
    classification_report = db.Column(db.JSON)
    confusion_matrix = db.Column(db.JSON)
    model_path = db.Column(db.String(500))
    vectorizer_path = db.Column(db.String(500))
    status = db.Column(db.String(30), nullable=False, default="queued")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class Prediction(db.Model):
    __tablename__ = "predictions"
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False, index=True)
    model_run_id = db.Column(db.BigInteger, db.ForeignKey("model_runs.id"), nullable=False)
    batch_id = db.Column(db.BigInteger)
    input_text = db.Column(db.Text, nullable=False)
    predicted_label = db.Column(db.Enum("Positif", "Negatif", "Netral"), nullable=False)
    actual_label = db.Column(db.Enum("Positif", "Negatif", "Netral"))
    row_number = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
