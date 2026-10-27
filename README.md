# Analisis Sentimen Komentar YouTube terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Algoritma Support Vector Machine

Status: fondasi Flask dan MySQL Laragon diuji; dua migration diterapkan pada database tes. Tes otomatis mencakup autentikasi, CSRF, role, impor CSV, lexicon, preprocessing Sastrawi, SVM dengan penanda holdout manual independen, evaluasi tiga kelas, serta route single/batch. Dashboard membaca jumlah aktual dari MySQL. UI publik telah diuji di browser pada lebar 390/768/1366px, tetapi halaman privat, seluruh interaksi, dan seluruh state belum diaudit visual. Data uji sintetis dalam tes bukan hasil penelitian. Holdout independen harus ditetapkan melalui proses anotasi terpisah yang terverifikasi; impor label CSV tidak otomatis memenuhi syarat.

## Persyaratan

Python 3.11 atau versi yang kompatibel dengan `requirements.txt`, MySQL 8, dan `uv` (atau pengelola virtualenv/pip). Versi paket di `requirements.txt` perlu divalidasi saat instalasi penuh.

## Setup lokal (Laragon, Windows)

Semua langkah di bawah dijalankan dari root proyek. Perintah memakai venv proyek (`.venv`), bukan Python global.

1. **Siapkan `.env`.** Salin `.env.example` menjadi `.env`, lalu isi `SECRET_KEY` dengan nilai acak kuat. Blok `DB_*` dipakai skrip setup untuk membuat database; `DATABASE_URL`/`TEST_DATABASE_URL` harus menunjuk nama database yang sama.

2. **Buat venv dan pasang dependensi.**

   ```bash
   uv venv .venv --python 3.11
   uv pip install --python .venv/Scripts/python.exe -r requirements.txt
   ```

3. **Buat database di MySQL Laragon dan jalankan migration.** Pastikan MySQL Laragon sudah menyala (default `127.0.0.1:3306`, user `root`, tanpa sandi).

   ```bash
   .venv/Scripts/python.exe python_instruct/setup_laragon_db.py
   ```

   Skrip ini membuat `sentiment_freeport` dan `sentiment_freeport_test` (utf8mb4), mencetak kedua URL koneksi, lalu menjalankan `flask db upgrade`. Aman dijalankan berulang. Bila MySQL memakai sandi, isi `DB_PASS` di `.env`; skrip tidak pernah mencetak sandi.

4. **Unduh kamus lexicon InSet.** Berkas tidak di-commit karena repo asal tidak menyatakan lisensi, dan `storage/` diabaikan Git.

   ```bash
   .venv/Scripts/python.exe python_instruct/fetch_lexicon.py
   ```

   Skrip mengunduh `positive.tsv` dan `negative.tsv` pada commit `9cb9d2971c575d64f4f0ed13c35048095f072a5b` dan memverifikasi SHA-256 terhadap nilai di `docs/lexicon_source.md`. Aplikasi menolak menjalankan pelabelan lexicon bila checksum tidak cocok. Folder kamus dapat dipindahkan lewat `LEXICON_FOLDER` di `.env`.

5. **Buat akun Superadmin.** Sandi dibaca dari environment variable, tidak pernah dari argumen perintah.

   ```bash
   SUPERADMIN_INITIAL_PASSWORD='sandi-kuat-minimal-12' \
     .venv/Scripts/python.exe -m flask --app run.py create-superadmin \
     --name "Nama Anda" --email "alamat@example.com"
   ```

6. **Jalankan aplikasi.**

   ```bash
   .venv/Scripts/python.exe run.py      # http://127.0.0.1:5055
   ```

   Cek `GET /health/db`: `200 {"status":"ok"}` bila MySQL terhubung, `503 {"status":"unavailable"}` bila tidak. Respons tidak memuat string koneksi. Aplikasi menolak start dengan pesan jelas bila `SECRET_KEY` atau `DATABASE_URL` kosong/tidak valid. Di lokal HTTP pakai `SESSION_COOKIE_SECURE=false`; pada HTTPS set `true`.

Folder `storage/uploads`, `storage/models`, dan `storage/lexicon` berada di luar `app/static` dan diabaikan Git. `TEST_DATABASE_URL` **wajib** menunjuk database tes terpisah karena fixture tes membuat dan menghapus tabel.

## Alur pelabelan (otomatis) dan perbedaan role

Pelabelan lexicon **berjalan otomatis** segera setelah CSV diimpor. Setelah berkas tersimpan, aplikasi membuat job background, melabeli baris dengan kamus InSet, lalu mengarahkan Anda ke halaman **Preprocessing** dengan dialog progres yang menampilkan `selesai/total` secara langsung. Tidak ada tombol yang perlu ditekan.

| | Pengguna biasa (`user`) | Superadmin |
|---|---|---|
| Pelabelan lexicon saat import | otomatis | otomatis |
| Tombol jalankan ulang lexicon | tidak ada | ada (**Jalankan Ulang Pelabelan Lexicon**) |
| Filter label di Preprocessing | Semua, Sudah dilabelkan, Positif, Negatif, Netral | semua filter + Perlu review, Label manual, Label lexicon |
| Baris yang perlu review | tidak ditampilkan (hanya jumlahnya) | ditampilkan lengkap |
| Kolom Sumber / Skor / Review | tidak ada | ada |
| Beri label manual | tidak boleh (403) | boleh |
| Tandai data uji independen | tidak boleh (403) | boleh |
| Halaman **Kelola Dataset** | tidak ada di menu (403) | ada |

Bila folder kamus belum tersedia, import **tetap berhasil** dan halaman menampilkan peringatan; Superadmin dapat menjalankan pelabelan setelah kamus dipasang. Kamus InSet diunduh dengan `python_instruct/fetch_lexicon.py` (lihat `docs/lexicon_source.md` untuk versi dan SHA-256).

### Halaman Kelola Dataset (Superadmin)

Menu **Kelola Dataset** (`/admin/datasets`) dipakai untuk meninjau hasil pelabelan otomatis: memilih dataset, memfilter (termasuk **Perlu review**), mengoreksi label satu per satu atau massal untuk baris terpilih, dan menandai/melepas data uji independen. Kolom **Status** menjelaskan asal label akhir: `accepted` (sudah dilabelkan lexicon), `review` (perlu review Superadmin), `resolved` (sudah diberi label manual). Setiap perubahan label tercatat di tabel `label_history`.

## Menetapkan data uji manual independen

Training SVM menolak berjalan tanpa data uji berlabel manual yang benar-benar terpisah, dan label hasil lexicon tidak dihitung sebagai ground truth (lihat `STRICT.md` §E4–E6). Alurnya:

1. Superadmin mengimpor CSV dengan kolom label manual, atau memberi label manual per komentar di halaman **Preprocessing** / **Kelola Dataset**.
2. Klik **Tandai data uji** pada komentar yang akan dijadikan holdout (di **Kelola Dataset** atau **Preprocessing**). Panel ringkasan menampilkan jumlah per kelas dan memberi tahu bila masih ada kelas yang belum terwakili.
3. Setelah ketiga kelas terwakili, jalankan **Klasifikasi SVM**. Tombol **Lepas data uji** membatalkan penandaan.

Hanya Superadmin yang dapat menandai; pengguna biasa tidak melihat kolom maupun tombolnya, dan endpoint-nya menolak dengan 403.

## Tes

```bash
.venv/Scripts/python.exe -m pytest tests -q
```

Tes integrasi MySQL memakai `TEST_DATABASE_URL` yang mengarah **hanya** ke database tes terpisah. Fixture membuat dan menghapus tabel; jangan gunakan URL database penelitian. Tes browser publik opsional memerlukan Playwright dan Edge: `BROWSER_BASE_URL=http://127.0.0.1:5055 uv run --no-project --python 3.11 --with-requirements requirements.txt --with playwright python -m pytest tests/test_browser_smoke.py -q` saat server berjalan. Port default `run.py` adalah 5055 (`PORT` dapat diubah). Tes UI privat lengkap belum tersedia.
