# Analisis Sentimen Komentar YouTube terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Algoritma Support Vector Machine

Status: fondasi Flask dan MySQL Laragon diuji; dua migration diterapkan pada database tes. Tes otomatis mencakup autentikasi, CSRF, role, impor CSV, lexicon, preprocessing Sastrawi, SVM dengan penanda holdout manual independen, evaluasi tiga kelas, serta route single/batch. Dashboard membaca jumlah aktual dari MySQL. UI publik telah diuji di browser pada lebar 390/768/1366px, tetapi halaman privat, seluruh interaksi, dan seluruh state belum diaudit visual. Data uji sintetis dalam tes bukan hasil penelitian. Holdout independen harus ditetapkan melalui proses anotasi terpisah yang terverifikasi; impor label CSV tidak otomatis memenuhi syarat.

## Persyaratan

Python 3.11 atau versi yang kompatibel dengan `requirements.txt`, MySQL 8, dan `uv` (atau pengelola virtualenv/pip). Versi paket di `requirements.txt` perlu divalidasi saat instalasi penuh.

## Setup lokal

1. Buat database MySQL dengan charset `utf8mb4`, misalnya `CREATE DATABASE sentiment_freeport CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`. Buat user MySQL dengan hak akses minimum dan isi kredensial lokal sesuai instalasi.
2. Salin `.env.example` menjadi `.env`. Ganti `SECRET_KEY` dengan nilai acak kuat dan `DATABASE_URL` dengan koneksi MySQL lokal. Jangan commit `.env`.
3. Instal dependensi: `uv venv` lalu `uv pip install --python .venv/Scripts/python.exe -r requirements.txt` (Windows). Alternatif: virtualenv dan pip sesuai platform.
4. Jalankan: `.venv/Scripts/python.exe run.py` dari root proyek. Di lokal HTTP, `SESSION_COOKIE_SECURE=false` saja; pada HTTPS gunakan `true`.
5. Cek `GET /health/db`: `200 {"status":"ok"}` jika MySQL dapat diakses; `503 {"status":"unavailable"}` jika gagal. Respons tidak memuat string koneksi. Aplikasi gagal start dengan pesan konfigurasi jika `SECRET_KEY` atau `DATABASE_URL` tidak ada/tidak valid.

Migration awal tersedia di `migrations/versions/`. Jalankan `uv run --no-project --python 3.11 --with-requirements requirements.txt flask --app run.py db upgrade` (gunakan dua migration berurutan) setelah menyiapkan `.env` dan database; jangan jalankan migration pada database yang memiliki tabel tak dikenal tanpa backup. Akun Superadmin dibuat lewat CLI `SUPERADMIN_INITIAL_PASSWORD` (minimum 12 karakter) dan `flask --app run.py create-superadmin --name "Nama" --email "alamat@example.com"`; jangan letakkan sandi dalam argumen command. Folder `storage/uploads` dan `storage/models` berada di luar `app/static` serta diabaikan Git. Database tes terpisah `sentiment_freeport_test` wajib digunakan untuk tes integrasi; jangan arahkan `TEST_DATABASE_URL` ke database produksi karena fixture membuat dan menghapus tabel.

## Tes

Tes unit: `uv run --no-project --python 3.11 --with-requirements requirements.txt python -m pytest tests -q`.

Tes integrasi MySQL memakai `TEST_DATABASE_URL` yang mengarah **hanya** ke database tes terpisah. Fixture membuat dan menghapus tabel; jangan gunakan URL database penelitian. Tes browser publik opsional memerlukan Playwright dan Edge: `BROWSER_BASE_URL=http://127.0.0.1:5055 uv run --no-project --python 3.11 --with-requirements requirements.txt --with playwright python -m pytest tests/test_browser_smoke.py -q` saat server berjalan. Port default `run.py` adalah 5055 (`PORT` dapat diubah). Tes UI privat lengkap belum tersedia.
