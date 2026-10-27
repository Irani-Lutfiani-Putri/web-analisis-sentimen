# Analisis Codebase & Schema Database — Web Analisis Sentimen PT Freeport

- **Repo:** `D:\rani\web` · remote `https://github.com/Irani-Lutfiani-Putri/web-analisis-sentimen.git`
- **Commit dianalisis:** `bba698c` (Initial commit: aplikasi analisis sentimen PT Freeport (Flask + MySQL)), working tree bersih
- **Tanggal analisis:** 2026-10-25
- **Metode:** pembacaan kode statis + 2 migration dijalankan ke MySQL lokal + 61 tes pytest + uji end-to-end HTTP/DB dengan data sintetis (data uji sudah dihapus kembali)

> Semua angka di dokumen ini berasal dari eksekusi nyata. Tidak ada hasil penelitian yang dikarang: data yang dipakai untuk verifikasi adalah kalimat sintetis dan sudah dibersihkan setelah pengujian.

---

## 1. Ringkasan Eksekutif

| Aspek | Kondisi |
|---|---|
| Stack | Flask 3.1.1 (app factory) + Flask-SQLAlchemy 3.1.1 + Flask-Login + Flask-WTF (CSRF) + Flask-Migrate/Alembic + PyMySQL + scikit-learn 1.7.1 + Sastrawi 1.0.1 + joblib |
| Struktur | Berlapis dan rapi: `routes/` (HTTP) → `services/` (logika) → `models/` (SQLAlchemy) → `templates/` + `static/css` |
| Ukuran kode | 3.340 baris total; Python ±1.600 baris (aplikasi ±900, tes ±800) |
| Database | MySQL, 6 tabel domain + `alembic_version`, 2 revisi migration, semua InnoDB/utf8mb4 |
| Tes | **60 passed, 1 skipped, 0 failed** (67,02 detik) — setelah perbaikan P0 |
| End-to-end (HTTP + DB) | **23/23 langkah PASS** lewat server HTTP sungguhan, dari database kosong |
| Kesimpulan | Fondasi, keamanan role, integritas ML, dan pipeline teks **sudah benar**. Dua penghambat fungsional (T-01, T-02) **sudah diperbaiki dan diverifikasi**; aplikasi kini dapat dijalankan end-to-end di Laragon. |

**Sisa risiko terbesar**

1. **Metadata reproduksibilitas eksperimen belum lengkap** (T-08): `vectorizer_config` hanya mencatat tipe, bukan parameter aktual; `random_state` tersimpan tetapi tidak dipakai menentukan split. Eksperimen tidak dapat direproduksi persis dari database saja.
2. **Tidak ada rate limiting login** dan pesan gagal login/registrasi masih teks polos (T-05, T-06).
3. **Batch testing tidak menyimpan `batch_id`/`actual_label`** dan tidak ada route untuk meninjau ulang hasilnya (T-10).

**Quick win yang tersisa**

1. Simpan parameter TF-IDF aktual + pakai `random_state`/`stratify` pada split.
2. Kembalikan kegagalan login/registrasi sebagai halaman form (401) dengan pesan, bukan teks polos.
3. Samakan pembacaan CSV antara impor dan batch testing (`csv.Sniffer`), karena CSV bertitik-koma kini lolos impor tetapi gagal di prediksi.

---

## 2. Inventaris & Ukuran

| Kelompok | File | Baris |
|---|---|---|
| Aplikasi inti | `run.py` (10), `app/__init__.py` (52), `app/config.py` (31), `app/extensions.py` (23), `app/cli.py` (27) | 143 |
| Model | `app/models/__init__.py` (24), `app/models/data.py` (91) | 115 |
| Route | `auth.py` (82), `datasets.py` (56), `preprocessing.py` (153), `classification.py` (29), `testing.py` (57), `pages.py` (8) | 385 |
| Service | `dataset_service.py` (42), `job_service.py` (69), `lexicon_service.py` (88), `preprocessing_service.py` (56), `training_service.py` (111), `prediction_service.py` (43) | 409 |
| Template | 10 file Jinja2 (`base`, `landing`, `auth/*2`, `dashboard`, `datasets/upload`, `preprocessing`, `classification`, `testing`) | ±230 |
| CSS | `app/static/css/style.css` (5.863 byte, satu baris minified) | 1 |
| Migration | `ff1d85f3da51_initial_relational_schema.py` (166), `7a0bc825f371_independent_holdout.py` (21), `env.py` (113) | 300 |
| Tes | 16 file, 61 fungsi `test_*` | ±800 |
| Dokumen | `AGENT.md` (213), `STRICT.md` (113), `AI_AGENT_BSD_TSD_Flask_MySQL.md` (545), PRD (125), `docs/lexicon_source.md` (5), README (23) | 1.024 |

Tidak ada `package.json`, `Dockerfile`, `Makefile`, CI workflow, atau `pyproject.toml`. Dependency dikelola murni lewat `requirements.txt` (versi di-pin).

---

## 3. Arsitektur & Alur Request

```text
run.py  (load_dotenv → create_app → app.run port 5055)
  └─ app/__init__.py:create_app()
       ├─ app.config.update(load_config())        # validasi SECRET_KEY + DATABASE_URL
       ├─ db / migrate / login_manager / csrf .init_app(app)
       ├─ errorhandler(413) → JSON {"status":"error"}
       ├─ register_blueprint: auth, pages, datasets, preprocessing, classification, testing
       ├─ cli: create-superadmin
       └─ GET /health/db → SELECT 1 → {"status":"ok"} / 503
```

| Method | Route | Fungsi | Akses | Status uji |
|---|---|---|---|---|
| GET | `/` | Landing | publik | 200 |
| GET | `/login` | Form login | publik | 200 |
| POST | `/login` | Login (CSRF) | publik | 302 sukses / 401 gagal / 400 tanpa CSRF |
| GET | `/register` | Form daftar | publik | 200 |
| POST | `/register` | Daftar, role dipaksa `user` | publik | 302 / 400 / 409 |
| POST | `/logout` | Hapus session | login | 302 |
| GET | `/dashboard` | Ringkasan dataset + distribusi label | login | 302 anon → `/login` |
| GET/POST | `/datasets/upload` | Import CSV | login (kolom label: Superadmin) | 200 / 403 / 400 |
| GET | `/preprocessing` | Lexicon + tabel komentar + preprocessing | login | 200 |
| POST | `/preprocessing/lexicon/run` | Jalankan lexicon (background) | login + pemilik dataset | 302 (503 bila kamus tidak ada) |
| POST | `/preprocessing/run` | Preprocessing teks (background) | login + pemilik | 302 |
| GET | `/preprocessing/jobs/<job_id>` | Polling progres | login + pemilik | 200 JSON |
| GET | `/preprocessing/labels/details` | Metadata label | **Superadmin** | 200 admin / 403 user |
| POST | `/preprocessing/labels/manual` | Ubah label manual | **Superadmin** | 302 / 403 |
| GET | `/classification` | Form training + hasil | login | 200 |
| POST | `/classification/train` | TF-IDF + SVM + evaluasi | login | 302 / 400 |
| GET | `/testing` | Form single & batch | login | 200 |
| POST | `/testing/single` | Prediksi 1 komentar | login | 200 / 400 |
| POST | `/testing/batch` | Prediksi CSV | login | 200 / 400 |
| GET | `/admin/health` | Probe role | **Superadmin** | 200 admin / 403 user |

**Route yang dirancang di TSD §10 tetapi belum ada:** `GET /datasets/<id>`, `GET/POST /admin/users`, `GET /testing/batch/<id>/results`.

Pola otorisasi yang dipakai konsisten: setiap resource diambil lewat `owned_dataset(id)` (`app/routes/preprocessing.py:42-46`) yang membandingkan `dataset.user_id` dengan `current_user.id` dan mengembalikan 404 (bukan 403) agar keberadaan resource tidak bocor.

---

## 4. Schema Database

Sumber kebenaran schema ada di dua tempat yang konsisten satu sama lain: definisi ORM di `app/models/` dan migration Alembic di `migrations/versions/`. DDL di bawah adalah hasil `SHOW CREATE TABLE` dari database `sentiment_freeport` setelah `flask db upgrade`.

### 4.1 Daftar tabel

| Tabel | Baris kolom | Peran |
|---|---|---|
| `users` | 7 | Akun + role |
| `datasets` | 11 | Metadata file CSV yang diimpor |
| `comments` | 19 | Satu baris komentar + seluruh metadata label |
| `label_history` | 7 | Audit perubahan label manual |
| `model_runs` | 19 | Satu eksperimen SVM + metrik + path artefak |
| `predictions` | 10 | Hasil single/batch testing |
| `alembic_version` | 1 | Versi migration (`7a0bc825f371`) |

### 4.2 Relasi

```text
users 1 ──N datasets ──1N comments ──1N label_history
users 1 ──N model_runs ──1N predictions
datasets 1 ──N model_runs
users 1 ──N predictions
users 1 ──N label_history (changed_by)
users 1 ──N comments (labeled_by, nullable)
```

### 4.3 `users`

```sql
CREATE TABLE `users` (
  `id`            bigint       NOT NULL AUTO_INCREMENT,
  `full_name`     varchar(150) NOT NULL,
  `email`         varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role`          enum('user','superadmin') NOT NULL,
  `created_at`    datetime     NOT NULL,
  `updated_at`    datetime     NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4.4 `datasets`

```sql
CREATE TABLE `datasets` (
  `id`                bigint       NOT NULL AUTO_INCREMENT,
  `user_id`           bigint       NOT NULL,
  `original_filename` varchar(255) NOT NULL,
  `stored_filename`   varchar(255) NOT NULL,
  `file_path`         varchar(500) NOT NULL,
  `row_count`         int          NOT NULL,
  `comment_column`    varchar(100) NOT NULL,
  `label_column`      varchar(100) DEFAULT NULL,
  `dataset_type`      enum('train','test','unassigned') NOT NULL,
  `status`            varchar(30)  NOT NULL,
  `created_at`        datetime     NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `stored_filename` (`stored_filename`),
  KEY `ix_datasets_user_id` (`user_id`),
  CONSTRAINT `datasets_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Nilai `status` yang benar-benar dipakai kode: `validated` (setelah impor) dan `processed` (setelah preprocessing). Nilai `uploaded` dan `failed` dari TSD §9.2 tidak pernah ditulis.

### 4.5 `comments`

```sql
CREATE TABLE `comments` (
  `id`                     bigint NOT NULL AUTO_INCREMENT,
  `dataset_id`             bigint NOT NULL,
  `row_number`             int    NOT NULL,
  `comment_text`           text   NOT NULL,
  `cleaned_text`           text   DEFAULT NULL,
  `manual_label`           enum('Positif','Negatif','Netral') DEFAULT NULL,
  `lexicon_label`          enum('Positif','Negatif','Netral') DEFAULT NULL,
  `lexicon_score`          decimal(10,6) DEFAULT NULL,
  `lexicon_version`        varchar(100) DEFAULT NULL,
  `lexicon_processed_at`   datetime DEFAULT NULL,
  `review_status`          varchar(30) DEFAULT NULL,
  `sentiment_label`        enum('Positif','Negatif','Netral') DEFAULT NULL,
  `label_source`           enum('manual','lexicon','review') DEFAULT NULL,
  `labeled_by`             bigint DEFAULT NULL,
  `labeled_at`             datetime DEFAULT NULL,
  `label_note`             varchar(500) DEFAULT NULL,
  `created_at`             datetime NOT NULL,
  `is_independent_holdout` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_comment_dataset_row` (`dataset_id`,`row_number`),
  KEY `labeled_by` (`labeled_by`),
  KEY `ix_comments_dataset_id` (`dataset_id`),
  CONSTRAINT `comments_ibfk_1` FOREIGN KEY (`dataset_id`) REFERENCES `datasets` (`id`),
  CONSTRAINT `comments_ibfk_2` FOREIGN KEY (`labeled_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Catatan penting:

- `is_independent_holdout` **NOT NULL tanpa default di level MySQL**. Migration `7a0bc825f371` menambah kolom dengan `server_default=sa.false()` lalu **menghapus default itu**. Akibatnya setiap `INSERT` mentah (phpMyAdmin, skrip, seed SQL) wajib menyebut kolom ini secara eksplisit, kalau tidak gagal. Lewat ORM aman karena `default=False` di model.
- `review_status` bertipe `varchar(30)` bebas, bukan enum. Nilai yang dipakai: `review`, `accepted`, `resolved`.
- Tiga kolom label hidup berdampingan sesuai STRICT.md §E1: `manual_label`, `lexicon_label`, `sentiment_label` (label akhir). Pemisahan ini benar dan auditabel.

### 4.6 `label_history`

```sql
CREATE TABLE `label_history` (
  `id`             bigint NOT NULL AUTO_INCREMENT,
  `comment_id`     bigint NOT NULL,
  `changed_by`     bigint NOT NULL,
  `previous_label` enum('Positif','Negatif','Netral') DEFAULT NULL,
  `new_label`      enum('Positif','Negatif','Netral') NOT NULL,
  `note`           varchar(500) DEFAULT NULL,
  `created_at`     datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `changed_by` (`changed_by`),
  KEY `ix_label_history_comment_id` (`comment_id`),
  CONSTRAINT `label_history_ibfk_1` FOREIGN KEY (`changed_by`) REFERENCES `users` (`id`),
  CONSTRAINT `label_history_ibfk_2` FOREIGN KEY (`comment_id`) REFERENCES `comments` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Tabel ini tidak diminta eksplisit oleh TSD §9, tetapi merupakan implementasi langsung STRICT.md §D8 (catat akun dan waktu perubahan label).

### 4.7 `model_runs`

```sql
CREATE TABLE `model_runs` (
  `id`                    bigint NOT NULL AUTO_INCREMENT,
  `user_id`               bigint NOT NULL,
  `dataset_id`            bigint NOT NULL,
  `experiment_name`       varchar(150) NOT NULL,
  `split_ratio`           varchar(20)  NOT NULL,
  `random_state`          int          NOT NULL,
  `vectorizer_config`     json DEFAULT NULL,
  `svm_config`            json DEFAULT NULL,
  `accuracy`              decimal(8,6) DEFAULT NULL,
  `precision_macro`       decimal(8,6) DEFAULT NULL,
  `recall_macro`          decimal(8,6) DEFAULT NULL,
  `f1_macro`              decimal(8,6) DEFAULT NULL,
  `classification_report` json DEFAULT NULL,
  `confusion_matrix`      json DEFAULT NULL,
  `model_path`            varchar(500) DEFAULT NULL,
  `vectorizer_path`       varchar(500) DEFAULT NULL,
  `status`                varchar(30)  NOT NULL,
  `created_at`            datetime     NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dataset_id` (`dataset_id`),
  KEY `ix_model_runs_user_id` (`user_id`),
  CONSTRAINT `model_runs_ibfk_1` FOREIGN KEY (`dataset_id`) REFERENCES `datasets` (`id`),
  CONSTRAINT `model_runs_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Contoh isi nyata dari uji plumbing (bukan hasil penelitian): `split_ratio='33:3'`, `accuracy=0.333333`, `confusion_matrix=[[0,0,1],[0,0,1],[0,0,1]]` — model hanya belajar kelas mayoritas karena data sintetis sengaja minimal.

### 4.8 `predictions`

```sql
CREATE TABLE `predictions` (
  `id`              bigint NOT NULL AUTO_INCREMENT,
  `user_id`         bigint NOT NULL,
  `model_run_id`    bigint NOT NULL,
  `batch_id`        bigint DEFAULT NULL,
  `input_text`      text   NOT NULL,
  `predicted_label` enum('Positif','Negatif','Netral') NOT NULL,
  `actual_label`    enum('Positif','Negatif','Netral') DEFAULT NULL,
  `row_number`      int DEFAULT NULL,
  `created_at`      datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `model_run_id` (`model_run_id`),
  KEY `ix_predictions_user_id` (`user_id`),
  CONSTRAINT `predictions_ibfk_1` FOREIGN KEY (`model_run_id`) REFERENCES `model_runs` (`id`),
  CONSTRAINT `predictions_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

`batch_id` **tanpa foreign key** karena tabel `prediction_batches` tidak dibuat (TSD §9.5 menyebutnya opsional). Akibatnya `batch_id` dan `actual_label` saat ini selalu `NULL` — lihat temuan T-11.

### 4.9 Index yang ada vs yang dibutuhkan

| Kebutuhan query | Index | Status |
|---|---|---|
| Komentar per dataset + pagination (`ORDER BY row_number`) | `ix_comments_dataset_id` + PK | Cukup untuk data kecil; tanpa composite `(dataset_id, row_number)` urutan diambil dari PK |
| Cek duplikat baris per dataset | `uq_comment_dataset_row` | ✔ |
| Pencarian teks `LIKE '%q%'` | tidak ada | Full scan (lihat T-13) |
| Dataset per pemilik | `ix_datasets_user_id` | ✔ |
| Eksperimen per pemilik | `ix_model_runs_user_id` | ✔ |
| Prediksi per pemilik | `ix_predictions_user_id` | ✔ |
| Riwayat label per komentar | `ix_label_history_comment_id` | ✔ |

---

## 5. Pipeline NLP & ML (apa yang benar)

1. **Preprocessing satu pintu.** `transform_stages()` di `app/services/preprocessing_service.py:26-34` menghasilkan empat tahap yang bisa diaudit (cleaning → case folding → stopword → stemming) dan `preprocess_text()` memakai tahap terakhir. Training dan inference memanggil fungsi yang sama (`training_service` memakai `cleaned_text`, `prediction_service.predict_single` memanggil `preprocess_text`).
2. **Negasi dipertahankan.** `NEGATIONS` dikeluarkan dari daftar stopword (`_stopwords()`), dan token negasi tidak di-stem. Diuji oleh `test_negation_survives_stopword_and_stemming`.
3. **TF-IDF bebas leakage.** `train_model()` memisahkan indeks holdout lebih dulu, lalu `vectorizer.fit_transform(train_texts)` dan `vectorizer.transform(test_texts)` (`training_service.py:45-48`). Tidak ada fit pada seluruh dataset.
4. **Test set hanya dari label manual independen.** Syarat di `training_service.py:70`: `is_independent_holdout and manual_label == sentiment_label and label_source == 'manual'`. Label hasil lexicon tidak pernah masuk test set — sesuai STRICT.md §F.
5. **Validasi kelas & duplikat.** Tiga kelas wajib ada di train dan test; teks duplikat (case-insensitive) ditolak di dalam test, di dalam train, dan lintas train/test.
6. **Evaluasi 3×3 + macro.** `confusion_matrix(labels=CLASSES)` dan `precision_recall_fscore_support(average='macro')`, `zero_division=0`; `classification_report` disimpan sebagai JSON.
7. **Tidak ada probabilitas palsu.** `SVC(kernel='linear', C=1.0)` tanpa `probability=True`; UI hanya menampilkan label.
8. **Pasangan artefak dijaga.** `load_run()` memverifikasi `model_path`/`vectorizer_path` harus tepat `<MODEL_FOLDER>/<run.id>/model.joblib` dan `.../vectorizer.joblib`, sehingga model satu eksperimen tidak bisa dipasangkan dengan vectorizer eksperimen lain.
9. **Lexicon konservatif.** `classify_comment()` mengembalikan `label=None, review=True` untuk: tanpa hit, skor 0, ada negasi, ada kata yang bertabrakan polaritas, atau campuran hit positif+negatif. Skor nol **tidak** dipaksa jadi Netral — sesuai STRICT.md §C5.

---

## 6. Temuan & Risk Register

Prioritas: **P0** memblokir tujuan penelitian · **P1** melanggar STRICT/PRD atau menyesatkan · **P2** kualitas/keberlanjutan.

| ID | Temuan | Dampak | Bukti | Prioritas |
|---|---|---|---|---|
| **T-01** | ~~Tidak ada jalur untuk menandai *holdout manual independen*.~~ **SELESAI** — route `POST /preprocessing/labels/holdout` (Superadmin), service `holdout_service.py`, kolom aksi per komentar, panel ringkasan per kelas, dan status di halaman Klasifikasi. | Training kini dapat dijalankan dari UI setelah ketiga kelas ditandai; tanpa penandaan tetap ditolak 400. | `app/services/holdout_service.py`, `app/routes/preprocessing.py:152-175`, `app/templates/preprocessing/index.html` | ~~P0~~ selesai |
| **T-02** | ~~Kamus lexicon tidak ada di repo dan tidak dapat dikonfigurasi.~~ **SELESAI** — `LEXICON_FOLDER` di config + `.env.example`, verifikasi SHA-256 terhadap commit InSet yang tercatat, pesan 503 yang menyebut path konfigurasi, dan skrip unduhan. | Lexicon berjalan dengan kamus resmi; checksum salah ditolak dengan pesan jelas. | `app/config.py:28`, `app/services/lexicon_service.py:8-51`, `python_instruct/fetch_lexicon.py` | ~~P0~~ selesai |
| **T-03** | ~~Tes `test_admin_can_label_owned_comment` bergantung pada artefak yang tidak di-commit.~~ **SELESAI** — tes kini menunggu job background selesai sebelum menegaskan hasil. | Suite hijau: 60 passed, 1 skipped. | `tests/test_lexicon_routes.py:88-104` | ~~P1~~ selesai |
| **T-04** | `prediction_service.predict_batch` tidak memakai `csv.Sniffer`, sedangkan `dataset_service.parse_csv` memakai. | CSV bertitik-koma/pipe diterima saat impor tetapi ditolak di batch testing — perilaku tidak konsisten untuk file yang sama. | `app/services/prediction_service.py:27` (`csv.DictReader` langsung); diverifikasi: dataset_service → 2 baris, prediction_service → `PredictionError` | **P1** |
| **T-05** | Tidak ada rate limiting pada `POST /login` dan `POST /register`. | Brute force kredensial tidak dibatasi. | `grep -rn "Limiter\|rate_limit" app/` → kosong; `requirements.txt` tanpa Flask-Limiter | **P1** |
| **T-06** | Kegagalan login/registrasi mengembalikan teks polos (401/400/409), padahal template sudah punya slot `{% if error %}` yang tidak pernah diisi. | UX buruk dan melanggar semangat STRICT.md §H4 (state harus jelas di halaman); pengguna kehilangan konteks form. | `app/routes/auth.py:35,54`; `app/templates/auth/login.html` punya `{% if error %}` | **P1** |
| **T-07** | `model_runs.status='failed'` tidak pernah tersimpan. Saat training melempar exception, `db.session.rollback()` menghapus baris run. | Tidak ada jejak eksperimen gagal; bertentangan dengan STRICT.md §F10 ("tampilkan error dan status gagal"). | `app/services/training_service.py:96-103` | **P1** |
| **T-08** | Metadata reproduksibilitas tidak lengkap: `vectorizer_config` hanya `{'type': 'TfidfVectorizer'}` tanpa parameter aktual; `random_state` disimpan tetapi tidak dipakai untuk split (split ditentukan manual oleh holdout). | Eksperimen tidak dapat direproduksi persis dari database saja. | `app/services/training_service.py:74`; parameter `random_state` hanya diteruskan ke dict hasil | **P1** |
| **T-09** | `is_independent_holdout` NOT NULL tanpa default di MySQL setelah migration kedua. | `INSERT` mentah (seed/manual/SQL) gagal bila kolom tidak disebut; jebakan saat data penelitian dimasukkan lewat alat lain. | `migrations/versions/7a0bc825f371_independent_holdout.py:16-17` (`server_default=sa.false()` lalu `alter_column(... server_default=None)`); `SHOW CREATE TABLE comments` | **P1** |
| **T-10** | Batch prediction tidak menyimpan `batch_id` dan `actual_label`; tidak ada tabel `prediction_batches`; route `GET /testing/batch/<id>/results` tidak ada. | Hasil batch hanya tampil sekali di response HTML; tidak bisa ditinjau ulang atau dievaluasi terhadap label aktual. | `app/routes/testing.py:52-56`; `batch_id`/`actual_label` hanya ada di model | **P1** |
| **T-11** | Route TSD §10 belum ada: `GET /datasets/<id>`, `GET/POST /admin/users`, `GET /testing/batch/<id>/results`. | Manajemen akun/role dan peninjauan dataset/batch tidak tersedia. | `grep -rn "admin/users\|datasets/<\|batch/<" app/routes/` → kosong | **P2** |
| **T-12** | Dashboard belum punya diagram batang distribusi sentimen seperti PRD Screen 5; hanya daftar teks. | Deviasi visual dari acuan PRD/prototype. | `app/templates/dashboard/index.html`; `grep -c "chart\|svg"` → 0 | **P1** |
| **T-13** | Pencarian komentar memakai `LIKE '%q%'` tanpa index teks. | Full table scan; melambat pada dataset besar (NFR Performance). | `app/routes/preprocessing.py:30` | **P2** |
| **T-14** | Job progres hanya di memori proses (`_jobs` dict + thread daemon). | Restart server menghilangkan progres; tidak aman untuk multi-worker/produksi. Diakui di docstring. | `app/services/job_service.py:1-8,14` | **P2** |
| **T-15** | `pandas` dideklarasikan di `requirements.txt` tetapi tidak dipakai satu baris pun. | Dependency mati; memperbesar image/instalasi. | `grep -rn pandas app/` → kosong | **P2** |
| **T-16** | Tidak ada halaman error 403/404/500 sendiri; `errorhandler(413)` mengembalikan JSON bahkan untuk form HTML. | Pengalaman pengguna tidak konsisten; STRICT.md §G10 hanya terpenuhi karena debug dimatikan. | `app/__init__.py:28-31` | **P2** |
| **T-17** | Tidak ada proteksi unggah ganda: `(user_id, original_filename)` tidak unik; dataset bisa diimpor berulang tanpa peringatan. | Duplikasi data antar-dataset dapat mencemari penelitian bila pengguna tidak sadar. | `datasets` DDL; `app/routes/datasets.py:41-46` | **P2** |
| **T-18** | Semua template dan `style.css` ditulis dalam satu baris (minified manual). | Sulit ditinjau/di-diff; rawan konflik saat beberapa orang mengedit. | ukuran file di §2 | **P2** |
| **T-19** | Tidak ada artefak deploy: tidak ada `gunicorn`/`waitress`, `Dockerfile`, atau dokumentasi produksi. | `app.run()` hanya untuk pengembangan. | `run.py`; `requirements.txt` | **P2** |

---

## 7. Tinjauan Keamanan (hasil uji langsung)

| Kontrol | Status | Bukti |
|---|---|---|
| Password di-hash (`werkzeug.security`) | ✔ | `app/models/__init__.py:19-23`; tes `test_register_ignores_submitted_admin_role_and_hashes_password` |
| Role tidak bisa di-inject saat registrasi | ✔ | `app/routes/auth.py:31` hardcode `role="user"` |
| Superadmin hanya lewat CLI + env password ≥12 | ✔ | `app/cli.py:16-19` |
| Endpoint Superadmin menolak user biasa di backend | ✔ | `GET /admin/health` → 403, `GET /preprocessing/labels/details` → 403, `POST /preprocessing/labels/manual` → 404 untuk non-pemilik |
| Metadata label tidak bocor ke user biasa | ✔ | Render `/preprocessing` sebagai user: kolom `Sumber`/`Skor`/`Review` tidak ada di HTML; route hanya mengisi field itu bila `role == 'superadmin'` (`preprocessing.py:79-81`) |
| CSRF pada semua form POST | ✔ | `csrf.init_app`; `POST /login` tanpa token → 400 |
| Cookie session `HttpOnly` + `SameSite=Lax` + `Secure` dari env | ✔ | `app/config.py:28-30` |
| Path upload di luar `static`, nama file UUID | ✔ | `app/routes/datasets.py:32-37` |
| Artefak model divalidasi sebelum dimuat | ✔ | `training_service.load_run()` |
| Pesan error tidak membocorkan connection string | ✔ | `test_malformed_database_url_rejected_without_leaking_value`; `/health/db` hanya `{"status": ...}` |
| Rate limit login | ✘ | T-05 |
| Kebijakan password (kompleksitas) | ✘ | hanya `len >= 12` |
| Verifikasi email / reset password | ✘ | tidak ada (di luar scope TSD) |
| Halaman error kustom | ✘ | T-16 |

---

## 8. Hasil Pengujian yang Dijalankan

### 8.1 Suite pytest

```text
.venv/Scripts/python.exe -m pytest tests -q
→ 60 passed, 1 skipped in 67.02s
```

- Skip: `tests/test_browser_smoke.py` (butuh Playwright + server berjalan).
- `test_admin_can_label_owned_comment` kini lulus: tes menunggu job lexicon background selesai sebelum menegaskan `lexicon_version` dan `review_status`.
- Prasyarat yang saya siapkan: database `sentiment_freeport` dan `sentiment_freeport_test`, `.env` lokal (gitignored), `.venv` Python 3.11.15 via `uv`, kamus di `storage/lexicon`.

### 8.2 End-to-end lewat server HTTP sungguhan (23/23 PASS)

Dijalankan dari **database kosong**: `DROP DATABASE` → `setup_laragon_db.py` → `fetch_lexicon.py` → `create-superadmin` → `run.py`, lalu klien HTTP memakai cookie jar dan CSRF asli (bukan `app.test_client()`).

```text
PASS GET /login                          PASS tandai holdout Positif/Negatif/Netral (302)
PASS POST /login (302 → /dashboard)      PASS ringkasan holdout siap
PASS POST /datasets/upload (30 baris)    PASS POST /classification/train (302)
PASS POST /preprocessing/lexicon/run     PASS hasil + confusion matrix dirender
PASS job lexicon selesai (30/30)         PASS confusion matrix 3x3
PASS job preprocessing selesai (30/30)   PASS POST /testing/single (Prediksi: Positif)
PASS panel holdout tampil (25 tombol)    PASS POST /testing/batch
PASS training ditolak tanpa holdout(400) PASS login user biasa
PASS form holdout ditemukan di HTML      PASS user biasa tidak melihat kontrol holdout
PASS satu komentar per kelas terpilih    PASS user biasa ditolak holdout (403)
                                         PASS user biasa /labels/details (403)
```

### 8.3 Verifikasi aturan lexicon (dataset terpisah)

| Skenario | Hasil |
|---|---|
| Dataset **tanpa** kolom label, lexicon dijalankan | 30/30 baris terisi `lexicon_version`; distribusi `Positif 5 / Negatif 6 / review 19` |
| Skor nol / ambigu | 19 komentar masuk `review`, tidak dipaksa `Netral` |
| Dataset **dengan** label manual, lexicon dijalankan | 0 baris tersentuh lexicon, 0 label berubah |
| SHA-256 kamus vs `docs/lexicon_source.md` | cocok persis untuk `positive.tsv` dan `negative.tsv` |

### 8.4 Kebersihan setelah verifikasi

Data sintetis dihapus: `users/datasets/comments/model_runs/predictions/label_history` = 0 baris (kecuali satu akun Superadmin lokal), `storage/models` dan `storage/uploads` dihapus, `storage/lexicon` dipertahankan, server dev dihentikan. Schema dan dua migration tetap ada di database `sentiment_freeport`.

---

## 9. Backlog Berprioritas

### P0 — memblokir tujuan penelitian (SELESAI, terverifikasi)

**P0-1 · Jalur penetapan holdout manual independen — SELESAI**
- Yang ditambahkan: `app/services/holdout_service.py` (aturan tunggal: `manual_label == sentiment_label` dan `label_source == 'manual'`), route `POST /preprocessing/labels/holdout` ber-`@superadmin_required`, kolom "Data uji independen" per komentar dengan tombol **Tandai sebagai data uji** / **Lepas tanda**, panel ringkasan per kelas, dan status holdout per dataset di halaman Klasifikasi.
- Bukti verifikasi (HTTP sungguhan): training sebelum penandaan → `400 Data uji manual independen belum tersedia`; setelah menandai 1 komentar per kelas → `302` dan `model_runs` berisi run `completed` dengan confusion matrix 3×3.
- Penjagaan: user biasa tidak melihat kolom/tombol dan mendapat `403` bila memanggil endpoint langsung; komentar tanpa label manual tidak bisa ditandai (pesan error di halaman); endpoint butuh CSRF (`400` tanpa token) dan `404` untuk ID tak dikenal.

**P0-2 · Ketersediaan kamus lexicon — SELESAI**
- Yang ditambahkan: `LEXICON_FOLDER` (default `storage/lexicon`) di `app/config.py` dan `.env.example`; `verify_inset()` memeriksa SHA-256 kedua berkas terhadap commit InSet `9cb9d297…`; `python_instruct/fetch_lexicon.py` mengunduh + memverifikasi; route mengembalikan 503 **beserta halaman Preprocessing dan pesan yang menyebut path konfigurasi**, bukan teks polos.
- Bukti verifikasi: kedua berkas diunduh dan SHA-256 **cocok persis** dengan `docs/lexicon_source.md`; `POST /preprocessing/lexicon/run` → `302`, job `completed 30/30`, 30/30 baris tanpa label manual terisi `lexicon_version`, distribusi `Positif 5 / Negatif 6 / review 19`, dan 19 komentar ambigu ditandai review (skor nol tidak dipaksa Netral).
- Penjagaan: dataset yang diimpor dengan label manual tidak tersentuh lexicon (`0` baris ber-`lexicon_version`, `0` label berubah) — sesuai STRICT.md §C3.

### P1 — kepatuhan STRICT/PRD

| ID | Perbaikan | Kriteria terima |
|---|---|---|
| P1-1 (T-04) | Pakai `csv.Sniffer` yang sama di `predict_batch`, atau ekstrak satu helper `read_csv()` untuk impor & prediksi | CSV `;` memberi hasil identik di `/datasets/upload` dan `/testing/batch` |
| P1-2 (T-05) | Tambah Flask-Limiter: 5 percobaan/menit per IP pada `/login`, 3/jam pada `/register` | Percobaan ke-6 → 429 |
| P1-3 (T-06) | Kembalikan `render_template('auth/login.html', error=...)` dengan status 401; sama untuk register | Respons 401 memuat form + pesan; tes `test_pages` tetap lulus |
| P1-4 (T-07) | Buat baris `ModelRun` berstatus `failed` sebelum rollback artefak, simpan pesan error ringkas | Eksperimen gagal tampil di halaman Klasifikasi sebagai "gagal", bukan hilang |
| P1-5 (T-08) | Simpan parameter TF-IDF aktual (`analyzer`, `ngram_range`, `min_df`, `max_features`) di `vectorizer_config` | Dua eksperimen dengan konfigurasi berbeda dapat dibedakan dari DB saja |
| P1-6 (T-09) | Beri `server_default` tetap atau dokumentasikan kewajiban kolom pada insert manual | `INSERT` tanpa kolom tidak gagal, atau README menyebut eksplisit |
| P1-7 (T-10) | Simpan `batch_id` (UUID/nomor urut) + `actual_label` bila CSV menyertakan kolom label; sediakan route hasil batch | Hasil batch dapat dibuka ulang dari ID |
| P1-8 (T-12) | Tambah diagram batang distribusi sentimen (SVG/CSS murni, tanpa dependency baru) di Dashboard | Tiga batang tampil dari `label_counts` DB; empty state tetap ada saat 0 data |

### P2 — kualitas

| ID | Perbaikan |
|---|---|
| P2-1 (T-11) | Implementasi `GET /datasets/<id>`, `GET/POST /admin/users`, `GET /testing/batch/<id>/results` sesuai TSD §10 |
| P2-2 (T-13) | Tambah index FULLTEXT pada `comments.comment_text` atau ganti ke `MATCH ... AGAINST` |
| P2-3 (T-14) | Pindahkan progres job ke tabel `jobs` MySQL agar tahan restart dan multi-worker |
| P2-4 (T-15) | Hapus `pandas` dari `requirements.txt` atau pakai untuk validasi CSV agar konsisten dengan STRICT.md §G1 |
| P2-5 (T-16) | Halaman error 403/404/500 monokromatik + `errorhandler` HTML vs JSON berdasarkan `Accept` |
| P2-6 (T-17) | Cegah unggah ganda: peringatan bila `(user_id, original_filename)` sudah ada, atau hash isi file |
| P2-7 (T-18) | Format ulang template & CSS (multi-baris) tanpa mengubah output HTML |
| P2-8 (T-19) | Tambah `waitress`/`gunicorn` + catatan deployment di README |

---

## 10. Perintah Reproduksi

```bash
cd /d/rani/web

# 1. virtualenv + dependency
uv venv .venv --python 3.11
uv pip install --python .venv/Scripts/python.exe -r requirements.txt

# 2. database
M=/c/laragon/bin/mysql/mysql-8.0.30-winx64/bin/mysql.exe
"$M" -h 127.0.0.1 -u root -e "CREATE DATABASE IF NOT EXISTS sentiment_freeport CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
"$M" -h 127.0.0.1 -u root -e "CREATE DATABASE IF NOT EXISTS sentiment_freeport_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 3. .env (jangan commit)
#    SECRET_KEY, DATABASE_URL, TEST_DATABASE_URL, SESSION_COOKIE_SECURE=false

# 4. migration
.venv/Scripts/python.exe -m flask --app run.py db upgrade

# 5. superadmin (password lewat env, bukan argumen)
SUPERADMIN_INITIAL_PASSWORD='...' .venv/Scripts/python.exe -m flask --app run.py create-superadmin \
  --name "Nama" --email "alamat@example.com"

# 6. tes
.venv/Scripts/python.exe -m pytest tests -q

# 7. jalankan
.venv/Scripts/python.exe run.py        # http://127.0.0.1:5055

# 8. inspeksi schema
"$M" -h 127.0.0.1 -u root sentiment_freeport -e "SHOW CREATE TABLE comments\G"
```

---

## 11. Kesimpulan

Fondasi teknis proyek ini sudah benar dan konsisten dengan `STRICT.md`: pemisahan route/service/model, TF-IDF bebas leakage, evaluasi tiga kelas dengan confusion matrix 3×3 dan macro average, pemisahan tegas `manual_label`/`lexicon_label`/`sentiment_label`, serta proteksi metadata pelabelan yang terbukti di level backend (403/404, bukan sekadar sembunyikan tombol).

**Dua penghambat P0 sudah diperbaiki dan diverifikasi lewat HTTP sungguhan dari database kosong**, sehingga alur wajib "Upload → Lexicon → Preprocessing → SVM → Evaluasi → Testing" kini dapat dilalui pengguna:

1. **Holdout manual independen** kini dapat ditetapkan dari UI oleh Superadmin, dengan ringkasan per kelas dan penjagaan role di backend.
2. **Kamus lexicon** kini dikonfigurasi (`LEXICON_FOLDER`), diverifikasi SHA-256 terhadap commit InSet yang tercatat, dan dapat diunduh lewat skrip — tidak lagi selalu 503.

Aplikasi juga dapat dijalankan lokal di Laragon dengan empat perintah: `setup_laragon_db.py`, `fetch_lexicon.py`, `create-superadmin`, `run.py`. Yang tersisa adalah perbaikan P1/P2 (reproduksibilitas eksperimen, rate limit login, hasil batch yang dapat ditinjau ulang) — tidak memblokir penelitian, tetapi memengaruhi kualitas bukti dan ketahanan aplikasi.

---

## 12. Perubahan alur pelabelan (2026-10-25)

Pelabelan lexicon tidak lagi berupa tombol manual untuk semua role, dan peninjauan label dipindahkan ke halaman khusus Superadmin.

| Perubahan | Sebelum | Sesudah | Bukti |
|---|---|---|---|
| Pemicu pelabelan lexicon | Tombol **Jalankan Pelabelan Lexicon** untuk semua role | Job background otomatis setelah `POST /datasets/upload` | `tests/test_auto_lexicon.py::test_upload_starts_lexicon_job_automatically` |
| Tombol lexicon untuk `user` | Tampil | Tidak dirender; diganti keterangan "dijalankan otomatis" | `tests/test_role_visibility.py`, verifikasi browser |
| Filter label | 7 opsi untuk semua role | `user`: 5 (semua, sudah, positif, negatif, netral); `superadmin`: 8 | `app/services/comment_query.py` |
| Baris `review` bagi `user` | Tampil tanpa label | Disaring di SQL, hanya jumlahnya yang dilaporkan | `test_role_visibility.py::test_user_sees_four_label_filters_and_no_review_rows` |
| CRUD label & holdout | Hanya inline di halaman Preprocessing | Halaman **Kelola Dataset** (`/admin/datasets`) + aksi massal | `tests/test_admin_datasets.py` |
| Pop-up progres | Tidak ada (endpoint job tidak dipakai UI) | `<dialog>` + polling `GET /preprocessing/jobs/<id>` | verifikasi browser: "400 dari 2232 (18%)" |
| Sumber aturan filter | Duplikat di route | Satu modul `app/services/comment_query.py` | — |

Bug yang ditemukan dan diperbaiki saat verifikasi: watcher progres me-reload halaman tanpa membuang parameter `?job=`, sehingga halaman me-reload berulang kali (terbukti dari log server yang berulang tiap detik). Diperbaiki dengan `history.replace` ke URL tanpa `job` sebelum reload.

Catatan kualitas data: pada 2.232 komentar nyata, lexicon InSet menandai **1.953 (87,5%) sebagai `review`** dan hanya memberi label 151 Positif + 128 Negatif. Ini konsekuensi kamus domain umum (microblog) pada teks pertambangan, sesuai `docs/lexicon_source.md` — bukan bug. Konsekuensinya beban peninjauan manual tinggi dan halaman **Kelola Dataset** menjadi jalur utama peneliti.

Hasil verifikasi akhir: **76 passed, 1 skipped, 0 failed**; E2E HTTP dua role **38/38 PASS**; data penelitian 2.232 baris utuh setelah import ulang bersih.
