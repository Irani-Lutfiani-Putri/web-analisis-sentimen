# Audit Sistem — Alur dan Konsep

> **Catatan historis:** Audit ini dilakukan sebelum perubahan konsep tanpa role. Temuan role, Superadmin, dan `/admin/datasets` sudah tidak berlaku. Dokumen konsep terbaru ada di `docs/ALUR-AKSES.md` dan `docs/superpowers/specs/2026-11-21-tanpa-role-design.md`.

- **Tanggal:** 21 November 2026
- **Workspace:** `D:\rani\website`
- **Commit:** `ea872f6` (`main`, ahead 1 dari `origin/main`)
- **Metode:** pembacaan kode statis, penelusuran route/service/model, dan eksekusi `pytest tests -q` pada MySQL lokal.
- **Lingkup:** alur sistem, konsep pipeline, integritas data/ML, otorisasi, operasional. Bukan audit visual menyeluruh.

---

## 1. Ringkasan

Aplikasi adalah sistem Flask + MySQL untuk analisis sentimen komentar YouTube tentang aktivitas pertambangan PT Freeport Indonesia. Konsep utamanya:

1. Impor CSV komentar.
2. Pelabelan otomatis InSet.
3. Review dan pelabelan manual oleh Superadmin.
4. Preprocessing teks Sastrawi.
5. Training TF-IDF + SVM linear dengan test set manual independen.
6. Evaluasi tiga kelas.
7. Inferensi single dan batch.

Fondasi teknisnya cukup kuat: pemisahan route/service/model, CSRF, hashing password, isolasi data per pemilik, label manual tidak ditimpa lexicon, dan TF-IDF hanya di-fit pada data training.

Namun sistem **belum aman untuk produksi multi-worker** dan **belum sepenuhnya sesuai STRICT.md**. Dua masalah paling serius:

- Job background disimpan di memori proses, sedangkan Gunicorn berjalan dengan 2 worker.
- CI tidak menyediakan kamus InSet, sehingga test yang sama yang dijalankan lokal gagal.

Status test aktual: **82 passed, 1 failed, 3 skipped** (138,05 detik). Kegagalan berasal dari kamus InSet yang tidak ada di `storage/lexicon`, bukan dari logika lexicon.

---

## 2. Konsep Sistem

### 2.1 Aktor dan hak akses

| Kemampuan | `user` | `superadmin` |
|---|---|---|
| Registrasi mandiri | ya, role dipaksa `user` | tidak |
| Impor CSV | ya | ya |
| Impor kolom label manual | tidak (403) | ya |
| Melihat baris `review` | tidak, difilter di SQL | ya |
| Melihat skor/sumber/status review | tidak | ya |
| Memberi label manual | tidak (403) | ya |
| Menandai data uji independen | tidak (403) | ya |
| Melatih SVM | terhalang karena holdout hanya Superadmin | ya |
| Kelola Dataset | tidak | ya |

### 2.2 Urutan pipeline yang dijaga sistem

```text
Upload CSV
  -> Pelabelan InSet otomatis
  -> Review / koreksi manual (Superadmin)
  -> Preprocessing teks
  -> Penentuan holdout manual (Superadmin)
  -> Training TF-IDF + SVM
  -> Evaluasi 3 kelas
  -> Testing single / batch
```

Urutan tidak dijaga oleh state machine eksplisit. Sebagian besar dijaga oleh kombinasi status dataset, kolom `lexicon_processed_at`, `cleaned_text`, `status='processed'`, dan flag holdout.

### 2.3 Tiga jenis label yang dipisahkan

| Kolom | Sumber | Boleh ditimpa |
|---|---|---|
| `lexicon_label` | kamus InSet | ya, saat lexicon dijalankan ulang |
| `sentiment_label` | lexicon atau manual | hanya oleh Superadmin lewat label manual |
| `manual_label` | Superadmin | hanya oleh Superadmin; tidak pernah oleh lexicon |

Aturan penting: `annotate_dataset()` melewati baris yang sudah punya `manual_label`. Ini memenuhi STRICT.md §C3.

### 2.4 Aturan lexicon

- Kata dicocokkan setelah lowercase dan tokenisasi sederhana.
- Skor = jumlah bobot kata yang cocok.
- Baris masuk `review` jika:
  - tidak ada kata kamus,
  - skor nol,
  - ada kata negasi,
  - ada kata yang muncul di polaritas positif dan negatif.
- Baris `review` tidak dipaksa menjadi Netral.
- Netral hanya muncul dari label manual.

Konsekuensi: dataset tanpa label manual Netral tidak bisa ditraining. Ini konsisten dengan aturan “jangan paksa Netral”, tetapi membuat peran `user` tidak bisa menyelesaikan pipeline sendirian.

### 2.5 Aturan training

- Hanya dataset milik user dan berstatus `processed`.
- Hanya baris dengan label valid dan bukan `review`.
- Test set hanya baris yang:
  - punya `manual_label`,
  - `label_source='manual'`,
  - `sentiment_label == manual_label`,
  - ditandai `is_independent_holdout`.
- Ketiga kelas wajib ada di training dan test.
- Teks duplikat antara train/test ditolak.
- TF-IDF di-fit hanya pada teks training.
- SVM linear, `C=1.0`.
- Evaluasi memakai confusion matrix 3 × 3 dan metrik macro.
- Model dan vectorizer disimpan berpasangan di `storage/models/<run_id>/`.

---

## 3. Arsitektur dan Alur Request

### 3.1 Komponen

```text
run.py
  -> create_app()
       -> load_config()          validasi SECRET_KEY + DATABASE_URL MySQL
       -> SQLAlchemy / Migrate / LoginManager / CSRF
       -> blueprint: auth, pages, datasets, preprocessing,
                     admin_datasets, classification, testing
       -> CLI: create-superadmin
       -> GET /health/db

routes/       HTTP, validasi form, otorisasi awal
services/     logika bisnis, query, lexicon, preprocessing, training, prediksi
models/       User, Dataset, Comment, LabelHistory, ModelRun, Prediction
templates/    Jinja2
static/       CSS, JS, Chart.js
migrations/   Alembic
```

### 3.2 Alur route utama

| Method | Route | Fungsi |
|---|---|---|
| GET | `/` | Landing publik |
| GET/POST | `/register` | Registrasi, role selalu `user` |
| GET/POST | `/login` | Login |
| POST | `/logout` | Logout + CSRF |
| GET | `/dashboard` | Ringkasan dataset terbaru milik user |
| GET/POST | `/datasets/upload` | Impor CSV; GET membuka modal dashboard |
| GET | `/preprocessing` | Lexicon, tabel komentar, filter, pagination |
| POST | `/preprocessing/lexicon/run` | Jalankan ulang lexicon (job) |
| POST | `/preprocessing/run` | Preprocessing teks (job) |
| GET | `/preprocessing/jobs/<job_id>` | Status job |
| POST | `/preprocessing/labels/manual` | Label manual (Superadmin) |
| POST | `/preprocessing/labels/holdout` | Tandai/lepas holdout (Superadmin) |
| GET | `/admin/datasets` | Kelola Dataset (Superadmin) |
| POST | `/admin/datasets/label` | Label satu baris |
| POST | `/admin/datasets/label/bulk` | Label massal, maksimal 200 |
| POST | `/admin/datasets/holdout` | Toggle holdout |
| GET | `/classification` | Form training + hasil eksperimen |
| POST | `/classification/train` | Latih SVM |
| GET | `/testing` | Form single/batch |
| POST | `/testing/single` | Prediksi satu komentar |
| POST | `/testing/batch` | Prediksi CSV batch |
| GET | `/health/db` | Health check database |

### 3.3 Alur data

```text
CSV
  -> parse_csv() validasi encoding/kolom/baris
  -> file privat storage/uploads/<uuid>.csv
  -> INSERT datasets + comments
  -> job lexicon (thread)
       -> load_inset() + verifikasi SHA-256
       -> annotate_dataset()
  -> redirect /preprocessing?dataset_id=...&job=...
  -> job preprocessing
       -> process_dataset()
       -> cleaned_text + status processed
  -> training
       -> train_model()
       -> ModelRun + model.joblib + vectorizer.joblib
  -> testing
       -> preprocess_text()
       -> vectorizer.transform()
       -> model.predict()
       -> INSERT predictions
```

### 3.4 Deployment

```text
GitHub Actions (test + deploy)
  -> SSH ke VPS
  -> clone release baru
  -> pip install requirements
  -> flask db upgrade
  -> switch symlink current
  -> restart systemd
  -> health check /health/db
  -> rollback symlink jika health check gagal
```

Service produksi memakai **Gunicorn 2 worker**.

---

## 4. Model Data

Enam tabel domain:

| Tabel | Isi |
|---|---|
| `users` | Akun, role, password hash |
| `datasets` | Metadata file, pemilik, status, kolom komentar/label |
| `comments` | Teks asli, hasil preprocessing, label lexicon/manual/final, holdout |
| `label_history` | Riwayat perubahan label manual |
| `model_runs` | Konfigurasi, metrik, confusion matrix, path artefak |
| `predictions` | Hasil single/batch |

Relasi utama:

```text
users 1---N datasets 1---N comments 1---N label_history
users 1---N model_runs 1---N predictions
datasets 1---N model_runs
```

Catatan: `predictions.batch_id` dan `predictions.actual_label` ada di skema, tetapi tidak pernah diisi. `prediction_batches` tidak ada.

---

## 5. Invariant yang Sudah Benar

Hal-hal berikut sudah dijaga dengan baik dan layak dipertahankan:

1. Password disimpan sebagai hash Werkzeug.
2. Registrasi tidak menerima role dari request.
3. CSRF aktif untuk seluruh POST.
4. Setiap dataset/komentar diverifikasi kepemilikannya sebelum diakses.
5. Baris `review` difilter di SQL untuk user biasa, sehingga pagination tetap konsisten.
6. Metadata internal (skor, sumber, pelabel, waktu) tidak dikirim ke user biasa.
7. Label manual tidak pernah ditimpa lexicon.
8. Lexicon memverifikasi SHA-256 file InSet.
9. Preprocessing menyimpan teks asli dan hasil bersih terpisah.
10. TF-IDF di-fit hanya pada training, bukan seluruh dataset.
11. Holdout harus berlabel manual dan ketiga kelas harus terwakili.
12. Duplikat teks antara training dan test ditolak.
13. Confusion matrix 3 × 3 dan metrik per kelas memakai hasil aktual.
14. Pasangan model/vectorizer divalidasi terhadap direktori eksperimen.
15. File upload, model, dan vectorizer berada di `storage/`, di luar static.
16. Health check tidak membocorkan connection string.
17. `conftest.py` menolak database tes yang salah nama.

---

## 6. Temuan

Severity:

- **P0**: memblokir produksi atau membuat sistem tidak dapat diandalkan.
- **P1**: melanggar aturan produk/riset, atau bug fungsional yang terlihat pengguna.
- **P2**: kualitas, dokumentasi, pemeliharaan, atau pengerasan tambahan.

### P0-1 — Job background tidak kompatibel dengan 2 worker Gunicorn

**Bukti:**
- `app/services/job_service.py:1-8` menyatakan job hanya di memori dan mengasumsikan satu proses.
- `deploy/analisis-sentimen.service:14-15` menjalankan Gunicorn `--workers 2`.
- `app/routes/preprocessing.py:93-101` membuat job di worker yang menangani request.
- `app/routes/preprocessing.py:118-125` mem-polls status lewat HTTP, yang bisa mendarat di worker lain.
- `--max-requests 1000` di service mendaur ulang worker; thread daemon ikut mati.

**Dampak:**
- Polling status bisa 404 karena job hanya ada di memori worker lain.
- Job lexicon/preprocessing bisa hilang di tengah proses.
- Progress dialog tidak dapat dipercaya di produksi.

**Perbaikan yang disarankan:**
- Simpan job di MySQL (tabel `jobs`) atau gunakan queue worker eksternal (RQ/Celery).
- Atau turunkan ke 1 worker sebagai solusi sementara, tetapi tetap rapuh terhadap restart.
- Tambahkan test yang mensimulasikan dua worker atau setidaknya job yang dipoll dari proses berbeda.

### P0-2 — CI tidak menyediakan kamus InSet, sehingga test gagal

**Bukti:**
- `tests/test_lexicon_routes.py:88-89` mengharapkan `POST /preprocessing/lexicon/run` menghasilkan 302.
- Route mengembalikan 503 jika `storage/lexicon` tidak berisi file valid (`app/routes/preprocessing.py:81-92`).
- `.gitignore:7` mengabaikan `storage/`.
- `.github/workflows/ci-cd.yml:48-73` tidak menjalankan `python_instruct/fetch_lexicon.py`.
- Hasil lokal: `test_admin_can_label_owned_comment` gagal dengan `503 == 302`, log: `Folder kamus tidak ditemukan: D:\rani\website\storage\lexicon`.

**Dampak:**
- Job `deploy` bergantung pada `test`; CI merah berarti deployment tidak pernah berjalan.
- Clean checkout tidak dapat menjalankan suite secara penuh.

**Perbaikan yang disarankan:**
- Tambahkan langkah `python python_instruct/fetch_lexicon.py` sebelum pytest di CI.
- Atau buat fixture tes yang menyediakan file InSet asli dengan checksum yang cocok; jangan memalsukan checksum karena akan melemahkan validasi.
- Simpan file kamus di cache CI untuk menghindari unduhan berulang.

### P1-1 — Login selalu membuka modal upload, termasuk saat dataset sudah ada

**Bukti:**
- `app/routes/auth.py:89-90`: `return redirect(url_for("auth.dashboard", upload=1))` tanpa kondisi.
- `STRICT.md` §B8: modal otomatis hanya untuk pengguna yang belum punya dataset; pengguna yang sudah punya dataset masuk Dashboard normal.

**Dampak:**
- Melanggar aturan produk.
- Pengguna lama dipaksa menutup modal setiap login.

**Perbaikan:**
- Cek jumlah dataset milik user sebelum redirect.
- Tambahkan test: user dengan dataset tidak mendapat `data-auto-open`.

### P1-2 — Halaman “Hasil Klasifikasi” tidak ada

**Bukti:**
- `STRICT.md` §B6 dan §B12 mewajibkan menu dan halaman terpisah “Hasil Klasifikasi”.
- `app/templates/base.html:3` tidak memuat menu tersebut.
- Hanya ada route `/classification` (`app/routes/classification.py:24-49`).
- Template `classification/index.html` menggabungkan form training dan hasil evaluasi.

**Catatan konflik dokumen:**
- `AGENT.md:141` justru mengatakan “tampilkan hasil evaluasi di halaman Klasifikasi; jangan menambah halaman utama Evaluasi terpisah”.
- `AGENT.md:15` menyatakan STRICT.md berprioritas lebih tinggi. Jadi keputusan yang konsisten saat ini adalah mengikuti STRICT: pisahkan halaman hasil.

**Dampak:**
- Checklist kelulusan STRICT.md §I belum terpenuhi.
- Navigasi tidak sesuai desain yang disetujui.

### P1-3 — Pagination hasil batch testing tidak berfungsi

**Bukti:**
- `app/routes/testing.py:75-84` memotong hasil hanya pada response POST.
- Template hasil batch membuat link ke `testing.index` dengan `page=...`.
- `app/routes/testing.py:16-19` untuk GET `/testing` tidak membaca `page` dan tidak memiliki hasil batch.
- `batch_result` hanya ada pada render POST.

**Dampak:**
- Tombol “Berikutnya”/“Sebelumnya” membuka halaman kosong.
- Hasil batch tidak dapat ditinjau ulang setelah response hilang.
- `Prediction.batch_id` dan `actual_label` tidak pernah diisi (`app/models/data.py:86,89`).

**Perbaikan:**
- Simpan batch dan hasilnya (tabel `prediction_batches` atau `batch_id` yang benar-benar dipakai).
- Sediakan `GET /testing/batch/<id>`.
- Atau render semua baris di client dan pagination hanya di UI.

### P1-4 — Metadata reproduksibilitas eksperimen belum memadai

**Bukti:**
- `app/services/training_service.py:14` menerima `random_state`, tetapi tidak dipakai untuk split.
- `app/services/training_service.py:42-44` hanya membuat `TfidfVectorizer()` dan `SVC(kernel='linear', C=1.0)`.
- `app/services/training_service.py:74-79` menyimpan `vectorizer_config={'type': 'TfidfVectorizer'}` dan `svm_config={'kernel': 'linear', 'C': 1.0}`.
- `test_ids` dihitung tetapi tidak disimpan.
- `ModelRun` tidak menyimpan versi lexicon, versi preprocessing, atau hash dataset.

**Dampak:**
- Eksperimen tidak dapat direproduksi persis dari database.
- `random_state=42` yang ditampilkan memberi kesan split acak, padahal split ditentukan manual oleh holdout.

**Perbaikan:**
- Simpan seluruh parameter TF-IDF/SVM aktual.
- Simpan ID komentar training/test atau hash-nya.
- Simpan versi lexicon, konfigurasi preprocessing, dan hash file dataset.
- Hapus `random_state` jika tidak digunakan, atau gunakan benar-benar.

### P1-5 — Training gagal tidak meninggalkan jejak `failed`

**Bukti:**
- `app/services/training_service.py:80-95`: `ModelRun` dibuat dengan status `running`, lalu `db.session.rollback()` saat dump gagal.
- Rollback menghapus baris run.
- `app/routes/classification.py:39-48` hanya menangkap `TrainingError`; error lain menjadi 500.
- `STRICT.md` §F10 meminta status gagal ditampilkan, bukan status sukses palsu.

**Dampak:**
- Tidak ada riwayat eksperimen gagal.
- Pengguna hanya melihat error umum.
- Artefak setengah jadi bisa tertinggal di storage.

**Perbaikan:**
- Commit `ModelRun` dengan status `failed` dan pesan error ringkas sebelum cleanup.
- Tangkap error I/O dan tampilkan pesan yang dapat ditindaklanjuti.

### P1-6 — Format CSV impor dan batch testing tidak konsisten

**Bukti:**
- `app/services/dataset_service.py:22-25` memakai `csv.Sniffer` dengan delimiter `, ; \t |`.
- `app/services/prediction_service.py:29` memakai `csv.DictReader` default (koma).
- CSV bertitik-koma lolos impor, tetapi gagal di batch testing.

**Dampak:**
- Pengguna mengira file yang sama valid, lalu ditolak di tahap testing.

**Perbaikan:**
- Ekstrak satu helper pembaca CSV dan gunakan di impor, batch, dan test.

### P1-7 — Tidak ada rate limiting login/register

**Bukti:**
- `app/routes/auth.py` tidak memakai limiter.
- `requirements.txt` tidak memuat Flask-Limiter atau sejenis.

**Dampak:**
- Brute force password tidak dibatasi.
- Registrasi massal tidak dibatasi.

**Perbaikan:**
- Tambahkan rate limit per IP + email untuk login, dan per IP untuk register.
- Tetap gunakan pesan error generik agar tidak membocorkan akun.

### P1-8 — Peran `user` tidak dapat menyelesaikan pipeline

**Bukti:**
- Training mensyaratkan holdout (`app/services/training_service.py:70-72`).
- Holdout hanya dapat ditandai Superadmin (`app/routes/preprocessing.py:138-160`, `app/routes/admin_datasets.py:116-131`).
- Label manual juga hanya Superadmin (`app/routes/preprocessing.py:163-184`).

**Dampak:**
- `user` bisa upload dan preprocessing, tetapi tidak bisa training/testing.
- Produk secara efektif hanya dapat dipakai oleh Superadmin.
- Ini didokumentasikan di README/ALUR-ROLE, tetapi bertentangan dengan kesan “aplikasi riset multi-user”.

**Keputusan yang perlu diambil:**
- Jadikan peneliti sebagai Superadmin, atau
- Beri user hak melabeli dataset miliknya sendiri dengan audit trail, atau
- Nyatakan user sebagai peran baca-saja dan sesuaikan UI/penamaan.

### P1-9 — Holdout dapat diubah tanpa audit, berpotensi leakage antar-eksperimen

**Bukti:**
- `app/services/holdout_service.py:28-38` hanya mengubah boolean.
- Tidak ada riwayat perubahan holdout.
- `ModelRun` tidak menyimpan komentar mana yang menjadi test.
- Menandai/melepas holdout setelah eksperimen dapat membuat baris yang pernah menjadi test masuk ke training eksperimen berikutnya.

**Dampak:**
- Integritas evaluasi antar-eksperimen sulit dibuktikan.
- “Independen” hanya berlaku dalam satu run, bukan sepanjang riwayat penelitian.

**Perbaikan:**
- Catat perubahan holdout di `label_history` atau tabel audit khusus.
- Simpan snapshot test set per `ModelRun`.
- Larang holdout yang sudah pernah menjadi test masuk training run berikutnya, atau beri peringatan eksplisit.

### P1-10 — Duplikasi upload tidak dicegah

**Bukti:**
- `app/models/data.py:10-22` tidak memiliki unique constraint pada `(user_id, original_filename)` atau hash konten.
- `app/routes/datasets.py:101` selalu membuat dataset baru.

**Dampak:**
- File yang sama dapat diimpor berulang.
- Data ganda mencemari distribusi dan training.
- Tidak ada mekanisme hapus dataset.

**Perbaikan:**
- Hitung hash isi file dan peringatkan/tolak duplikat.
- Atau sediakan konfirmasi eksplisit dan tampilkan dataset yang sudah ada.

### P1-11 — Deployment menjalankan migration tanpa backup database

**Bukti:**
- `deploy/deploy-analisis-sentimen:55-67` menjalankan `flask db upgrade` langsung.
- Rollback hanya mengembalikan symlink `current`; tidak mengembalikan skema/data.
- DDL MySQL tidak transaksional secara penuh.

**Dampak:**
- Migration yang gagal di tengah dapat meninggalkan skema tidak konsisten.
- Data penelitian berisiko hilang tanpa backup.

**Perbaikan:**
- `mysqldump` sebelum migration, simpan dengan timestamp.
- Uji migration pada salinan database.
- Dokumentasikan prosedur restore.

### P2 — Temuan kualitas dan konsistensi

1. **Dokumentasi tidak konsisten.**
   - `prd_analisis_sentimen_komentar_youtube(1).md:4` masih menyebut isu BBM; STRICT.md membatasi hanya Freeport.
   - PRD §5 masih monokrom; STRICT.md memakai palet magenta/pastel.
   - `docs/ALUR-ROLE.md:21` menyebut `classification_service.py` yang tidak ada.
   - `docs/ANALISIS-CODEBASE.md` menganalisis commit lama `bba698c` dan path `D:\rani\web`.
   - README menyatakan panel status server-side tetap tersedia tanpa JS; kenyataannya status job tidak dirender server-side.

2. **Kode/field mati.**
   - `GET /preprocessing/labels/details` (`app/routes/preprocessing.py:128-135`) tidak dipakai template.
   - `app/templates/datasets/upload.html` tidak pernah dirender; route memakai modal dashboard.
   - `Prediction.batch_id` dan `Prediction.actual_label` tidak pernah diisi.
   - `Dataset.dataset_type='test'` tidak pernah dipakai.
   - `pandas` ada di `requirements.txt:7` tetapi tidak diimpor di `app/`.

3. **Pencarian komentar memakai `LIKE '%q%'` tanpa index** (`app/services/comment_query.py:82`). Full table scan pada dataset besar.

4. **Migration holdout menghapus server default** (`migrations/versions/7a0bc825f371_independent_holdout.py:16-17`). Insert manual yang tidak menyebut kolom akan gagal.

5. **Error 413 selalu JSON** (`app/__init__.py:30-32`), termasuk untuk form upload HTML. Tidak ada halaman 403 khusus.

6. **Dialog upload belum punya `aria-labelledby`** ke judul modal; tombol tutup hanya teks `x`. Perlu penguatan aksesibilitas sesuai STRICT.md §B14.

7. **Tidak ada security header** seperti CSP, HSTS, atau X-Frame-Options. Bergantung pada reverse proxy yang tidak didokumentasikan.

8. **Training berjalan di request thread.** SVM pada dataset besar dapat memblokir worker hingga timeout Gunicorn 300 detik. Pertimbangkan background job seperti lexicon/preprocessing.

9. **Testing selalu memakai run terbaru** (`app/routes/testing.py:12-13`), tanpa pemilih model/dataset dan tanpa menampilkan ID eksperimen di UI. Traceability lemah.

10. **CI memakai MariaDB 10.11**, sedangkan target produksi MySQL 8. Perbedaan perilaku enum/DDL perlu diuji.

11. **Test memakai `db.create_all()`, bukan `flask db upgrade`.** Migration tidak diuji di CI; drift skema baru terdeteksi saat deploy.

12. **Fallback tanpa JavaScript belum lengkap.** Progress job hanya dari polling JS; tidak ada status job server-side di HTML.

13. **Tidak ada staging** dan tidak ada smoke test produksi selain `/health/db`.

14. **`gunicorn` tidak ada di `requirements.txt`**, tetapi service produksi memanggil `shared/venv/bin/gunicorn`. Harus dipastikan sudah dipasang di server atau tambahkan ke requirements.

15. **Deploy README memuat IP dan user VPS.** Bukan rahasia, tetapi sebaiknya tidak disebar di repo publik.

---

## 7. Bukti Pengujian

Perintah yang dijalankan:

```powershell
$env:SECRET_KEY='test-secret'
$env:DATABASE_URL='mysql+pymysql://root:@127.0.0.1:3306/sentiment_freeport?charset=utf8mb4'
$env:TEST_DATABASE_URL='mysql+pymysql://root:@127.0.0.1:3306/sentiment_freeport_test?charset=utf8mb4'
$env:SESSION_COOKIE_SECURE='false'
D:\rani\web\.venv\Scripts\python.exe -m pytest tests -q
```

Hasil:

```text
1 failed, 82 passed, 3 skipped in 138.05s
```

Kegagalan:

```text
tests/test_lexicon_routes.py::test_admin_can_label_owned_comment
assert 503 == 302
WARNING app:preprocessing.py:85 Lexicon unavailable:
Folder kamus tidak ditemukan: D:\rani\website\storage\lexicon
```

Penyebab: `storage/lexicon` kosong. Ini bukan kegagalan logika, tetapi kegagalan reproducibility dan CI.

Test yang di-skip:

- `test_browser_smoke.py` karena `BROWSER_BASE_URL` tidak diset.
- Test lexicon otomatis karena kamus tidak tersedia.
- Sebagian test lain bergantung pada ketersediaan `TEST_DATABASE_URL`; pada run ini database tersedia.

---

## 8. Urutan Perbaikan yang Disarankan

### Sebelum demo/sidang

1. Jalankan `python_instruct/fetch_lexicon.py`, lalu ulangi test sampai hijau.
2. Perbaiki CI: tambahkan langkah unduh lexicon sebelum pytest.
3. Perbaiki modal login: hanya buka otomatis jika user belum punya dataset.
4. Perbaiki pagination batch atau sembunyikan kontrol pagination sampai hasil dipersistensi.
5. Putuskan dan rapikan halaman “Hasil Klasifikasi” sesuai STRICT.md.
6. Samakan pembaca CSV impor dan batch.
7. Tambahkan rate limit login/register.

### Sebelum produksi

8. Ganti job in-memory dengan job persisten/queue, atau turunkan Gunicorn ke 1 worker sebagai mitigasi sementara.
9. Tambahkan backup database sebelum migration.
10. Tambahkan `gunicorn` ke requirements atau dokumentasikan provisioning venv.
11. Simpan status `failed` untuk training yang gagal.
12. Simpan parameter eksperimen, test IDs, versi lexicon, dan hash dataset.
13. Tambahkan audit perubahan holdout.

### Peningkatan riset

14. Simpan snapshot test set per eksperimen.
15. Tambahkan pemilih model/dataset di halaman Testing.
16. Tambahkan halaman riwayat batch dan prediksi.
17. Dokumentasikan protokol pemilihan holdout dan batasannya.
18. Selaraskan PRD, AGENT, STRICT, README, dan ALUR-ROLE agar tidak saling bertentangan.

---

## 9. Batas Audit

- Tidak ada perubahan kode yang dilakukan dalam audit ini.
- UI tidak diuji dengan browser pada semua halaman privat.
- Tidak ada pengujian beban, konkurensi, atau multi-worker Gunicorn.
- Tidak ada pengujian migration dari database kosong.
- Tidak ada pengujian keamanan dinamis (misalnya pemindaian header atau fuzzing).
- Hasil test bergantung pada MySQL lokal dan ketersediaan file InSet.
