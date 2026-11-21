# Tanpa Role dan Halaman Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hapus konsep role dari aplikasi, buat semua akun hasil register setara, dan pindahkan review, label manual, serta holdout ke halaman `/labels` yang tidak ada di sidebar.

**Architecture:** Kolom `users.role` dihapus. Registrasi membuat akun tanpa role. Otorisasi menjadi `login_required` plus kepemilikan dataset. `comment_query` memisahkan query Preprocessing yang hanya menampilkan label akhir dari query halaman labels yang menampilkan semua baris. Blueprint `admin_datasets` diganti menjadi blueprint `labels`.

**Tech Stack:** Flask 3.1, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, MySQL, Jinja2, pytest.

**Spec:** `docs/superpowers/specs/2026-11-21-tanpa-role-design.md`

## Global Constraints

- Kolom `users.role` dihapus. Tidak ada nilai `superadmin`, `admin`, atau `user` sebagai role.
- Register tidak menerima role dari request. Akun baru langsung bisa login.
- Semua akun hanya melihat dataset miliknya sendiri.
- Preprocessing hanya menampilkan baris dengan `sentiment_label IS NOT NULL` dan `review_status != 'review'`.
- Halaman `/labels` menampilkan baris review dan baris tanpa label. Default filter `review`.
- Teks tombol: `Hitung Ulang Label Otomatis`.
- Teks pendamping: `Label manual yang sudah Anda tetapkan tidak berubah.`
- Teks antarmuka tidak memakai kata `lexicon`, `superadmin`, `admin`, atau `user` sebagai role.
- Tidak ada auto-login setelah register. Pengguna diarahkan ke `/login`.
- Tidak ada menu Review dan Label atau Kelola Dataset di sidebar.
- Semua POST tetap memakai CSRF.
- Semua label dan holdout diverifikasi terhadap dataset milik akun yang login.
- Aturan label akhir hanya berlaku pada query halaman Preprocessing. `process_dataset` tetap memproses semua baris agar baris yang dilabeli manual setelahnya sudah punya `cleaned_text`.
- Tidak mengubah pipeline TF-IDF, SVM, evaluasi, atau testing.
- Tidak ada em dash di teks yang ditulis.
- Test membutuhkan `TEST_DATABASE_URL` dan file InSet di `storage/lexicon`.

---

## Review Focus

1. Database lama berisi `users.role` NOT NULL. Migration harus menghapus kolom tanpa merusak baris pengguna.
2. Baris dengan `sentiment_label NULL` dan `review_status NULL` harus hilang dari Preprocessing, tetapi muncul di `/labels`.
3. Akun B tidak boleh memberi label atau holdout pada komentar milik akun A lewat POST langsung.
4. Jika kamus InSet tidak ada, upload tetap berhasil dan semua baris harus bisa dilabeli manual di `/labels`.
5. Akun tanpa role harus bisa menyelesaikan label manual, holdout, training, dan testing.

---

### Task 1: Hapus Role dari Model, Registrasi, Auth, dan Schema

**Files:**
- Modify: `app/models/__init__.py`
- Modify: `app/routes/auth.py`
- Modify: `app/__init__.py`
- Delete: `app/cli.py`
- Create: `migrations/versions/20261121_drop_user_role.py`
- Modify: `tests/test_auth.py`
- Modify: `tests/test_schema.py`

**Interfaces:**
- Consumes: `User` model, `create_app()`.
- Produces: `User` tanpa atribut `role`; register membuat `User(full_name, email, password_hash)`; `superadmin_required` sementara menjadi `login_required` saja sampai Task 5; tidak ada command `create-superadmin`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_auth.py`:

```python
def test_register_creates_account_without_role(client):
    response = client.post("/register", data={
        "full_name": "Peneliti",
        "email": "tanpa-role@example.test",
        "password": "rahasia-kuat-123",
    })
    assert response.status_code == 302
    with client.application.app_context():
        user = db.session.execute(
            db.select(User).filter_by(email="tanpa-role@example.test")
        ).scalar_one()
        assert not hasattr(user, "role")
```

Add to `tests/test_schema.py`:

```python
def test_users_table_has_no_role_column(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL MySQL terpisah belum tersedia")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    with app.app_context():
        db.create_all()
        columns = {item["name"] for item in inspect(db.engine).get_columns("users")}
        assert "role" not in columns
        db.drop_all()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_auth.py::test_register_creates_account_without_role tests/test_schema.py::test_users_table_has_no_role_column -v`
Expected: FAIL because `User` still has `role`.

- [ ] **Step 3: Remove role from the model and registration**

In `app/models/__init__.py`, remove:

```python
role = db.Column(db.Enum("user", "superadmin", name="user_role"), nullable=False, default="user")
```

In `app/routes/auth.py`, change register to:

```python
user = User(full_name=name, email=email)
```

Change `superadmin_required` temporarily to a login-only guard so imports keep working:

```python
def superadmin_required(fn):
    return login_required(fn)
```

Keep `admin_health` until Task 5. Remove the `abort` import if unused.

In `app/__init__.py`, remove:

```python
from app.cli import create_superadmin
app.cli.add_command(create_superadmin)
```

Delete `app/cli.py`.

- [ ] **Step 4: Add the migration**

Create `migrations/versions/20261121_drop_user_role.py`:

```python
"""Drop user role.

Revision ID: 20261121_drop_role
Revises: 7a0bc825f371
"""
from alembic import op
import sqlalchemy as sa

revision = "20261121_drop_role"
down_revision = "7a0bc825f371"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("users", "role")


def downgrade():
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("user", "superadmin", name="user_role"),
            nullable=False,
            server_default="user",
        ),
    )
```

- [ ] **Step 5: Run the focused tests**

Run: `pytest tests/test_auth.py::test_register_creates_account_without_role tests/test_schema.py::test_users_table_has_no_role_column -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/models/__init__.py app/routes/auth.py app/__init__.py migrations/versions/20261121_drop_user_role.py tests/test_auth.py tests/test_schema.py
git rm app/cli.py
git commit -m "refactor: remove user role from model and registration"
```

---

### Task 2: Pisahkan Query Preprocessing dan Labels

**Files:**
- Modify: `app/services/comment_query.py`
- Modify: `app/routes/preprocessing.py`
- Modify: `app/routes/admin_datasets.py`
- Create: `tests/test_preprocessing_visibility.py`

**Interfaces:**
- Consumes: `Comment`, `Dataset`.
- Produces:
  - `PREPROCESS_FILTER_KEYS: tuple[str, ...]`
  - `LABELS_FILTER_KEYS: tuple[str, ...]`
  - `normalize_filter(label: str, allowed_keys: tuple[str, ...]) -> str`
  - `filter_options(allowed_keys: tuple[str, ...]) -> list[dict]`
  - `build_query(dataset_id: int, q: str, label: str, include_review: bool = False)`
  - `paginate(dataset_id: int, q: str, label: str, page_arg: int | None, include_review: bool = False)`
  - `pending_review_count(dataset_id: int) -> int`

- [ ] **Step 1: Write the failing visibility tests**

Create `tests/test_preprocessing_visibility.py` with a fixture that creates one user, one dataset, and five comments:

```python
rows = [
    ("tambang bagus", "Positif", "lexicon", "accepted"),
    ("tambang merusak", "Negatif", "lexicon", "accepted"),
    ("tambang biasa", "Netral", "lexicon", "accepted"),
    ("tidak buruk", None, "review", "review"),
    ("entah apa", None, None, None),
]
```

Add:

```python
def test_preprocessing_hides_review_and_unlabeled_rows(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "tambang bagus" in html
    assert "tambang merusak" in html
    assert "tambang biasa" in html
    assert "tidak buruk" not in html
    assert "entah apa" not in html


def test_preprocessing_pending_count_includes_review_and_unlabeled(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "2 komentar menunggu label" in html
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_preprocessing_visibility.py -v`
Expected: FAIL because unlabeled rows are still shown and the pending count excludes them.

- [ ] **Step 3: Rewrite `comment_query.py`**

Remove all role helpers. Use these exact constants and ordering:

```python
LABEL_FILTERS = {"positif": "Positif", "negatif": "Negatif", "netral": "Netral"}
PREPROCESS_FILTER_KEYS = ("semua", "sudah", "positif", "negatif", "netral")
LABELS_FILTER_KEYS = ("semua", "sudah", "positif", "negatif", "netral", "review", "manual", "lexicon")
FILTER_TEXTS = {
    "semua": "Semua label",
    "sudah": "Sudah dilabelkan",
    "positif": "Positif",
    "negatif": "Negatif",
    "netral": "Netral",
    "review": "Perlu label",
    "manual": "Label manual",
    "lexicon": "Label otomatis",
}
```

`build_query` must apply this base filter when `include_review=False`:

```python
query = query.filter(
    Comment.sentiment_label.is_not(None),
    db.func.coalesce(Comment.review_status, "") != "review",
)
```

The `review` filter must use:

```python
db.or_(Comment.sentiment_label.is_(None), Comment.review_status == "review")
```

`pending_review_count` must count:

```python
db.or_(Comment.sentiment_label.is_(None), Comment.review_status == "review")
```

- [ ] **Step 4: Update the preprocessing route and keep the old admin page importable**

In `app/routes/preprocessing.py`:

- Remove `superadmin_required` import and all role branches.
- Call `paginate(..., include_review=False)`.
- Call `normalize_filter(..., PREPROCESS_FILTER_KEYS)`.
- Call `filter_options(PREPROCESS_FILTER_KEYS)`.
- Remove `context["is_superadmin"]`.
- Set `context["pending_review"] = pending_review_count(dataset.id)`.
- Set `context["labels_url"] = f"/labels?dataset_id={dataset.id}"` for now. Task 5 replaces it with `url_for("labels.index", dataset_id=dataset.id)` after the blueprint exists.
- Remove `label_details`, `set_holdout_flag`, and `manual_label` routes.

In `app/routes/admin_datasets.py`, keep the page functional until Task 5:

- Call `comment_query.normalize_filter(..., comment_query.LABELS_FILTER_KEYS)`.
- Call `comment_query.paginate(..., include_review=True)`.
- Call `comment_query.filter_options(comment_query.LABELS_FILTER_KEYS)`.
- Remove `current_user.role` arguments.

- [ ] **Step 5: Run the focused tests**

Run: `pytest tests/test_preprocessing_visibility.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/comment_query.py app/routes/preprocessing.py tests/test_preprocessing_visibility.py
git commit -m "refactor: hide review and unlabeled comments from preprocessing"
```

---

### Task 3: Buka Label Manual, Holdout, dan Impor Label

**Files:**
- Modify: `app/services/lexicon_service.py`
- Modify: `app/services/holdout_service.py`
- Modify: `app/routes/datasets.py`
- Modify: `tests/test_lexicon_db.py`
- Modify: `tests/test_upload.py`

**Interfaces:**
- Consumes: `Comment`, `LabelHistory`.
- Produces:
  - `update_manual_label(comment, label: str, user_id: int, note: str | None = None) -> None`
  - `set_holdout(comment, value: bool) -> None`
  - Upload menerima `label_column` dari akun mana pun.

- [ ] **Step 1: Write the failing tests**

In `tests/test_lexicon_db.py`, create one owner without role and call:

```python
update_manual_label(comment, "Positif", owner_id, "ditinjau ulang")
```

Assert history and label. In `tests/test_upload.py`, replace the 403 test with:

```python
def test_account_can_import_manual_labels(client):
    web, token = client
    response = web.post("/datasets/upload", data={
        "csrf_token": token,
        "comment_column": "isi",
        "label_column": "kategori",
        "file": (io.BytesIO(b"isi,kategori\nTambang berjalan,Positif\n"), "labels.csv"),
    }, content_type="multipart/form-data")
    assert response.status_code == 200
    with web.application.app_context():
        comment = db.session.execute(db.select(Comment)).scalar_one()
        assert comment.manual_label == "Positif"
        assert comment.label_source == "manual"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_lexicon_db.py tests/test_upload.py::test_account_can_import_manual_labels -v`
Expected: FAIL because services still require `superadmin` and upload returns 403.

- [ ] **Step 3: Remove role checks**

In `app/services/lexicon_service.py`, change the signature to `update_manual_label(comment, label, user_id, note=None)`. Remove the `User` import and the admin role check. Keep label validation and `LabelHistory` writes.

In `app/services/holdout_service.py`, change to `set_holdout(comment, value)`. Remove the `User` import and role check. Keep the manual label eligibility check.

In `app/routes/admin_datasets.py`, update the holdout call to `set_holdout(comment, value)` so the page stays functional until Task 5.

In `app/routes/datasets.py`, remove:

```python
if label_column and current_user.role != "superadmin":
    return _dashboard_modal(...)
```

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_lexicon_db.py tests/test_upload.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/lexicon_service.py app/services/holdout_service.py app/routes/datasets.py tests/test_lexicon_db.py tests/test_upload.py
git commit -m "refactor: allow every account to label and mark holdout"
```

---

### Task 4: Bersihkan Halaman Preprocessing

**Files:**
- Modify: `app/templates/preprocessing/index.html`
- Modify: `tests/test_preprocessing_visibility.py`
- Modify: `tests/test_preprocessing_pagination.py`

**Interfaces:**
- Consumes: `pending_review`, `labels_url`, `comments` dengan field `id`, `text`, `label`.
- Produces: Preprocessing tanpa metadata, tanpa form manual, dengan tombol hitung ulang untuk semua akun.

- [ ] **Step 1: Extend the failing tests**

Add to `tests/test_preprocessing_visibility.py`:

```python
def test_preprocessing_shows_rerun_and_labels_link(dataset):
    client = login(dataset.app, "visibility@test.local")
    html = client.get(f"/preprocessing?dataset_id={dataset.id}").data.decode()
    assert "Hitung Ulang Label Otomatis" in html
    assert "Buka Review dan Label (2)" in html
    assert "<th>Sumber</th>" not in html
    assert "<th>Skor</th>" not in html
    assert "/preprocessing/labels/manual" not in html
```

Add to `tests/test_preprocessing_pagination.py`:

```python
def test_preprocessing_only_paginates_labelled_rows(paged):
    client, _ = login(paged.app)
    html = client.get(f"/preprocessing?dataset_id={paged.dataset_id}").data
    assert b"24 komentar" in html
```

Adjust the fixture so 6 of 30 rows have `review_status="review"` and all of them also have a non-null label. The test proves review rows are excluded before pagination.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_preprocessing_visibility.py tests/test_preprocessing_pagination.py -v`
Expected: FAIL because the current template still has role branches and metadata columns.

- [ ] **Step 3: Rewrite the template**

In `app/templates/preprocessing/index.html`:

- Remove every `current_user.role` and `is_superadmin` branch.
- Always render the rerun form with button text `Hitung Ulang Label Otomatis`.
- Add helper text `Label manual yang sudah Anda tetapkan tidak berubah.`
- Show `Buka Review dan Label ({{ pending_review }})` linking to `labels_url`.
- Remove the holdout summary panel.
- Remove columns Sumber, Skor, Review, Pelabelan manual, dan Data uji independen.
- Keep the filter select, search, pagination, comparisons table, and progress dialog.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_preprocessing_visibility.py tests/test_preprocessing_pagination.py -v`
Expected: PASS after fixture updates.

- [ ] **Step 5: Commit**

```bash
git add app/templates/preprocessing/index.html tests/test_preprocessing_visibility.py tests/test_preprocessing_pagination.py
git commit -m "refactor: simplify preprocessing page"
```

---

### Task 5: Tambah Blueprint dan Halaman Labels

**Files:**
- Create: `app/routes/labels.py`
- Create: `app/templates/labels/index.html`
- Delete: `app/routes/admin_datasets.py`
- Delete: `app/templates/admin_datasets/index.html`
- Modify: `app/__init__.py`
- Modify: `app/routes/auth.py`
- Modify: `app/routes/preprocessing.py`
- Create: `tests/test_labels.py`

**Interfaces:**
- Consumes: `comment_query` functions from Task 2, `update_manual_label`, `set_holdout`, `holdout_summary`.
- Produces:
  - `labels.index` GET `/labels`
  - `labels.save_label` POST `/labels/label`
  - `labels.save_label_bulk` POST `/labels/label/bulk`
  - `labels.toggle_holdout` POST `/labels/holdout`
  - `labels.legacy_index` GET `/admin/datasets`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_labels.py` with a fixture that creates two accounts without roles, one dataset for account A, and four comments:

```python
rows = [
    ("tambang bagus", "Positif", "lexicon", "accepted"),
    ("tambang merusak", "Negatif", "lexicon", "accepted"),
    ("tidak buruk", None, "review", "review"),
    ("entah", None, None, None),
]
```

Tests:

```python
def test_labels_defaults_to_review_and_includes_unlabeled(page):
    client = login(page.app, "a@test.local")
    html = client.get(f"/labels?dataset_id={page.dataset_id}").data.decode()
    assert "tidak buruk" in html
    assert "entah" in html
    assert "tambang bagus" not in html
    assert 'value="review" selected' in html


def test_labels_filter_list(page):
    client = login(page.app, "a@test.local")
    html = client.get(f"/labels?dataset_id={page.dataset_id}").data.decode()
    for key in ("semua", "sudah", "positif", "negatif", "netral", "review", "manual", "lexicon"):
        assert f'value="{key}"' in html


def test_save_label_writes_history(page):
    client, token = login_with_token(page.app, "a@test.local")
    response = client.post("/labels/label", data={
        "csrf_token": token, "comment_id": page.review_id, "label": "Netral",
    })
    assert response.status_code == 302
    with page.app.app_context():
        comment = db.session.get(Comment, page.review_id)
        assert comment.manual_label == "Netral"
        assert comment.sentiment_label == "Netral"
        assert comment.label_source == "manual"
        assert db.session.scalar(db.select(db.func.count(LabelHistory.id))) == 1


def test_bulk_label_applies_to_selected_rows(page):
    client, token = login_with_token(page.app, "a@test.local")
    response = client.post("/labels/label/bulk", data={
        "csrf_token": token,
        "dataset_id": page.dataset_id,
        "label": "Negatif",
        "comment_ids": [str(page.review_id), str(page.unlabeled_id)],
    })
    assert response.status_code == 302
    with page.app.app_context():
        rows = db.session.execute(
            db.select(Comment).filter(Comment.id.in_([page.review_id, page.unlabeled_id]))
        ).scalars().all()
        assert all(row.manual_label == "Negatif" for row in rows)


def test_holdout_requires_manual_label(page):
    client, token = login_with_token(page.app, "a@test.local")
    response = client.post("/labels/holdout", data={
        "csrf_token": token, "comment_id": page.review_id, "value": "1",
    })
    assert response.status_code == 302
    assert "error=" in response.headers["Location"]
    with page.app.app_context():
        assert db.session.get(Comment, page.review_id).is_independent_holdout is False


def test_holdout_toggle_after_label(page):
    client, token = login_with_token(page.app, "a@test.local")
    client.post("/labels/label", data={
        "csrf_token": token, "comment_id": page.review_id, "label": "Positif",
    })
    client.post("/labels/holdout", data={
        "csrf_token": token, "comment_id": page.review_id, "value": "1",
    })
    with page.app.app_context():
        assert db.session.get(Comment, page.review_id).is_independent_holdout is True


def test_other_account_cannot_label_foreign_comment(page):
    client, token = login_with_token(page.app, "b@test.local")
    response = client.post("/labels/label", data={
        "csrf_token": token, "comment_id": page.review_id, "label": "Positif",
    })
    assert response.status_code == 404


def test_legacy_admin_datasets_redirects(page):
    client = login(page.app, "a@test.local")
    response = client.get(f"/admin/datasets?dataset_id={page.dataset_id}")
    assert response.status_code == 302
    assert "/labels" in response.headers["Location"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_labels.py -v`
Expected: FAIL with 404 for `/labels`.

- [ ] **Step 3: Create `app/routes/labels.py`**

Use this shape:

```python
bp = Blueprint("labels", __name__)
MAX_BULK = 200
VALID_LABELS = ("Positif", "Negatif", "Netral")


@bp.get("/labels")
@login_required
def index():
    datasets = db.session.execute(
        db.select(Dataset).filter_by(user_id=current_user.id)
        .order_by(Dataset.id.desc()).limit(50)
    ).scalars().all()
    requested = request.args.get("dataset_id", type=int)
    dataset = next((item for item in datasets if item.id == requested), None) or (datasets[0] if datasets else None)
    q = (request.args.get("q") or "").strip()[:100]
    label = comment_query.normalize_filter(
        request.args.get("label") or "review", comment_query.LABELS_FILTER_KEYS
    )
    comments, total_filtered, page, total_pages = [], 0, 1, 1
    counts, pending, holdout = {}, 0, None
    if dataset:
        comments, total_filtered, page, total_pages = comment_query.paginate(
            dataset.id, q, label, request.args.get("page", type=int), include_review=True
        )
        counts = comment_query.label_counts(dataset.id)
        pending = comment_query.pending_review_count(dataset.id)
        holdout = holdout_summary(dataset.id)
    rows = [...]
    return render_template("labels/index.html", ...)
```

`save_label`, `save_label_bulk`, and `toggle_holdout` mirror the old `admin_datasets` routes but use `url_for("labels.index")` and call `update_manual_label(comment, label, current_user.id, note)` and `set_holdout(comment, value)`.

Add:

```python
@bp.get("/admin/datasets")
@login_required
def legacy_index():
    return redirect(url_for("labels.index", **request.args.to_dict()))
```

- [ ] **Step 4: Register the blueprint and remove the old one**

In `app/__init__.py`, replace the `admin_datasets` import and registration with `labels`. Delete `app/routes/admin_datasets.py`.

In `app/routes/preprocessing.py`, replace the temporary `labels_url` literal with `url_for("labels.index", dataset_id=dataset.id)`.

In `app/routes/auth.py`, remove the temporary `superadmin_required` function and the `admin_health` route. Remove `app/templates/admin_datasets/index.html`.

- [ ] **Step 5: Create the labels template**

Create `app/templates/labels/index.html` from the old `admin_datasets/index.html` with:

- Title `Review dan Label`.
- Description `Periksa komentar yang belum punya label pasti, lalu tetapkan label manual. Data di halaman ini hanya berasal dari dataset Anda.`
- Form actions `labels.save_label`, `labels.save_label_bulk`, `labels.toggle_holdout`.
- Default filter `review`.
- No text `Superadmin`, `Kelola Dataset`, or `role`.
- Dataset selector, counts, holdout summary, table, pagination, bulk controls.

Delete `app/templates/admin_datasets/index.html`.

- [ ] **Step 6: Run focused tests**

Run: `pytest tests/test_labels.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/routes/labels.py app/templates/labels/index.html app/__init__.py tests/test_labels.py
git rm app/routes/admin_datasets.py app/templates/admin_datasets/index.html
git commit -m "feat: add hidden labels page and remove admin datasets"
```

---

### Task 6: Bersihkan Navigasi dan Teks Role

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/templates/preprocessing/index.html`
- Modify: `app/templates/dashboard/index.html`
- Delete: `app/templates/datasets/upload.html`
- Create: `tests/test_navigation.py`

**Interfaces:**
- Consumes: current user session.
- Produces: sidebar tanpa role dan tanpa menu labels; blok akun tanpa role; teks tombol final.

- [ ] **Step 1: Write the failing navigation tests**

Create `tests/test_navigation.py`:

```python
def test_sidebar_has_no_role_or_labels_menu(client):
    client.post("/register", data={
        "full_name": "Peneliti", "email": "nav@test.local", "password": "rahasia-kuat-123",
    })
    client.post("/login", data={"email": "nav@test.local", "password": "rahasia-kuat-123"})
    html = client.get("/dashboard").data.decode()
    assert "Kelola Dataset" not in html
    assert "Review dan Label" not in html
    assert "Super Admin" not in html
    assert ">Admin<" not in html


def test_register_redirects_to_login(client):
    response = client.post("/register", data={
        "full_name": "Peneliti", "email": "login@test.local", "password": "rahasia-kuat-123",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_navigation.py -v`
Expected: FAIL because sidebar still contains `Kelola Dataset` and role text.

- [ ] **Step 3: Update the base template**

In `app/templates/base.html`:

- Remove the `current_user.role == 'superadmin'` link to `admin_datasets`.
- Remove the `Super Admin` / `User` text from the account block. Keep the name and email.
- Keep `Dashboard`, `Preprocessing`, `Klasifikasi`, `Testing`, `Logout`.

- [ ] **Step 4: Update copy**

In `app/templates/preprocessing/index.html`:

- Button `Hitung Ulang Label Otomatis`.
- Helper `Label manual yang sudah Anda tetapkan tidak berubah.`
- Alert lexicon uses `kamus sentimen`, never `lexicon`.

In `app/templates/dashboard/index.html`, remove any role reference if present.

Delete `app/templates/datasets/upload.html` because the route renders the dashboard modal and the file is unused.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/test_navigation.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/templates/base.html app/templates/preprocessing/index.html app/templates/dashboard/index.html tests/test_navigation.py
git commit -m "refactor: remove role navigation and labels menu"
```

---

### Task 7: Perbarui Seluruh Test dan Fixture

**Files:**
- Modify: `tests/test_auth.py`
- Modify: `tests/test_auto_lexicon.py`
- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_lexicon_db.py`
- Modify: `tests/test_lexicon_routes.py`
- Modify: `tests/test_preprocessing_db.py`
- Modify: `tests/test_preprocessing_pagination.py`
- Modify: `tests/test_schema.py`
- Modify: `tests/test_training_db.py`
- Modify: `tests/test_training_eligibility.py`
- Modify: `tests/test_upload.py`
- Delete: `tests/test_role_visibility.py`
- Delete: `tests/test_admin_datasets.py`

**Interfaces:**
- Consumes: all routes and services from Tasks 1 to 6.
- Produces: suite tanpa referensi `role`, `/admin/datasets`, atau `/preprocessing/labels/manual`.

- [ ] **Step 1: Remove every role argument**

Run: `rg -n "role=|superadmin|/admin/datasets|/preprocessing/labels" tests`

For each hit:

- Remove `role="user"` and `role="superadmin"` from `User(...)`.
- Replace `/admin/datasets` with `/labels`.
- Replace `/preprocessing/labels/manual` with `/labels/label`.
- Replace `/preprocessing/labels/holdout` with `/labels/holdout`.
- Delete tests that only assert role gates.
- Change `logged_in(app, "superadmin")` to `logged_in(app)`.

- [ ] **Step 2: Rewrite `tests/test_lexicon_routes.py`**

Use two accounts without roles:

- Account A owns the dataset.
- Account B tries to run lexicon and label A's comment.
- Tests:
  - `test_account_can_open_labels`
  - `test_other_account_cannot_run_lexicon`
  - `test_other_account_cannot_label_foreign_comment`
  - `test_invalid_manual_label_is_rejected`
  - `test_lexicon_rerun_uses_background_job`

Keep the real lexicon requirement and the 60 second job wait.

- [ ] **Step 3: Rewrite `tests/test_auto_lexicon.py`**

Remove the `role` parameter from `login`. The manual label import test now logs in as a normal account. Keep the assertions that imported manual labels are not overwritten.

- [ ] **Step 4: Update `tests/test_training_eligibility.py` and `tests/test_training_db.py`**

Remove all `role` arguments. Keep the holdout rules unchanged. Add:

```python
def test_any_account_can_train_after_holdout(...):
    # create three classes, one manual holdout per class, then train
    run = train_dataset(dataset_id, owner_id, tmp_path)
    assert run.status == "completed"
```

Use the existing synthetic 24 row fixture in `test_training_db.py`.

- [ ] **Step 5: Remove obsolete test files**

Delete `tests/test_role_visibility.py` and `tests/test_admin_datasets.py`. Their coverage moves to `tests/test_preprocessing_visibility.py` and `tests/test_labels.py`.

- [ ] **Step 6: Run the full suite**

Run: `pytest tests -q`
Expected: all tests pass except tests that require missing InSet files. If InSet is missing, run `python python_instruct/fetch_lexicon.py` first.

- [ ] **Step 7: Commit**

```bash
git add tests
git rm tests/test_role_visibility.py tests/test_admin_datasets.py
git commit -m "test: update suite for roleless accounts and labels page"
```

---

### Task 8: Perbarui Dokumentasi

**Files:**
- Modify: `README.md`
- Rename: `docs/ALUR-ROLE.md` to `docs/ALUR-AKSES.md`
- Modify: `STRICT.md`
- Modify: `AGENT.md`
- Modify: `prd_analisis_sentimen_komentar_youtube(1).md`

**Interfaces:**
- Consumes: final behavior from Tasks 1 to 7.
- Produces: docs tanpa konsep role dan tanpa instruksi Superadmin.

- [ ] **Step 1: Update README**

Replace the role table with:

- Register membuat akun.
- Login memakai akun yang sudah dibuat.
- Semua akun setara.
- Setiap akun hanya melihat dataset sendiri.
- Review dan label manual ada di `/labels`, tidak di sidebar.
- Tombol `Hitung Ulang Label Otomatis` tersedia untuk semua akun.
- Setup tidak lagi memakai `create-superadmin`.

- [ ] **Step 2: Rename and rewrite the access doc**

```bash
git mv docs/ALUR-ROLE.md docs/ALUR-AKSES.md
```

Rewrite the title and contents to explain:

- Satu jenis akun.
- Register, login, dan isolasi dataset.
- Preprocessing hanya label akhir.
- `/labels` untuk review, label manual, dan holdout.
- Tombol hitung ulang label otomatis.

- [ ] **Step 3: Update STRICT and AGENT**

In `STRICT.md`:

- Remove `Superadmin` and `user` role language.
- Replace privacy rules with per-account privacy.
- Keep research integrity rules for manual labels and holdout.
- Keep the rule that manual labels are never overwritten.

In `AGENT.md`:

- Remove instructions to create or use Superadmin.
- Replace role steps with account ownership checks.
- Keep the pipeline and testing rules.

- [ ] **Step 4: Update PRD personas**

Replace `Admin Sistem` with `Pengguna`. Remove mentions of role-based access that no longer exist.

- [ ] **Step 5: Verify no stale role references**

Run:

```bash
rg -n "superadmin|Superadmin|Super Admin|role=|role ==|role !=|Kelola Dataset|/admin/datasets" README.md STRICT.md AGENT.md docs app/templates
```

Expected: no hits except historical audit files and migration downgrade notes.

- [ ] **Step 6: Commit**

```bash
git add README.md STRICT.md AGENT.md prd_analisis_sentimen_komentar_youtube\(1\).md docs/ALUR-AKSES.md
git rm docs/ALUR-ROLE.md
git commit -m "docs: document roleless accounts and labels page"
```

---

### Task 9: Verifikasi Akhir

**Files:**
- No new files.
- Verify migration, tests, and UI copy.

- [ ] **Step 1: Ensure the sentiment dictionary exists**

Run:

```bash
python python_instruct/fetch_lexicon.py
```

Expected: `Kamus lexicon siap di storage/lexicon.`

- [ ] **Step 2: Run the full test suite**

Run:

```powershell
$env:SECRET_KEY='test-secret'
$env:DATABASE_URL='mysql+pymysql://root:@127.0.0.1:3306/sentiment_freeport?charset=utf8mb4'
$env:TEST_DATABASE_URL='mysql+pymysql://root:@127.0.0.1:3306/sentiment_freeport_test?charset=utf8mb4'
$env:SESSION_COOKIE_SECURE='false'
pytest tests -q
```

Expected: all tests pass. Browser smoke may skip when `BROWSER_BASE_URL` is not set.

- [ ] **Step 3: Test the migration on an old schema**

Create a temporary database, apply the old revision, insert one user with each old role, then upgrade:

```bash
mysql -u root -e "DROP DATABASE IF EXISTS sentiment_freeport_migration; CREATE DATABASE sentiment_freeport_migration CHARACTER SET utf8mb4"

DATABASE_URL='mysql+pymysql://root:@127.0.0.1:3306/sentiment_freeport_migration?charset=utf8mb4' \
SECRET_KEY='migration-test-secret' \
flask --app run.py db upgrade 7a0bc825f371

mysql -u root sentiment_freeport_migration -e "
INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) VALUES
('Lama User', 'lama-user@test.local', 'x', 'user', NOW(), NOW()),
('Lama Admin', 'lama-admin@test.local', 'x', 'superadmin', NOW(), NOW());
"

DATABASE_URL='mysql+pymysql://root:@127.0.0.1:3306/sentiment_freeport_migration?charset=utf8mb4' \
SECRET_KEY='migration-test-secret' \
flask --app run.py db upgrade
```

Then verify:

```bash
mysql -u root sentiment_freeport_migration -e "SHOW COLUMNS FROM users; SELECT COUNT(*) FROM users;"
```

Expected: `role` is absent; two user rows remain.

- [ ] **Step 4: Check the UI copy**

Run:

```bash
rg -n "lexicon|superadmin|Superadmin|Super Admin|Kelola Dataset|role" app/templates app/routes
```

Expected: no user-facing hits. Internal service names are allowed.

- [ ] **Step 5: Commit any verification fixes**

```bash
git add -A
git commit -m "test: verify roleless migration and labels flow"
```

---

## Self-Review Notes

- Spec coverage: schema role removal in Task 1, query split in Task 2, permission removal in Task 3, preprocessing UI in Task 4, labels page in Task 5, navigation and copy in Task 6, tests in Task 7, docs in Task 8, migration verification in Task 9.
- Type consistency: `update_manual_label(comment, label, user_id, note=None)`, `set_holdout(comment, value)`, `build_query(..., include_review=False)`, `paginate(..., include_review=False)`.
- Review focus tests are placed in Tasks 1, 2, 3, 5, and 7.
- No task implements the Hasil Klasifikasi page because it is explicitly out of scope.
