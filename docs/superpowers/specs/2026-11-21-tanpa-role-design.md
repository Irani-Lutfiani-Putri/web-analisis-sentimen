# Desain: Tanpa Role dan Halaman Label Terpisah

- **Tanggal:** 21 November 2026
- **Workspace:** `D:\rani\website`
- **Status:** draft, menunggu persetujuan
- **Menggantikan:** desain `2026-11-21-admin-tunggal-design.md` dan aturan role di `docs/ALUR-ROLE.md`

## 1. Maksud

Hapus konsep role sepenuhnya. Tidak ada `superadmin`, tidak ada `admin`, dan tidak ada `user` biasa. Register membuat akun. Setelah register, pengguna login dengan akun yang baru dibuat. Semua akun setara.

Setiap akun hanya melihat dan mengelola dataset miliknya sendiri. Pelabelan otomatis InSet tetap berjalan setelah upload CSV. Halaman Preprocessing hanya menampilkan komentar yang sudah punya label akhir. Baris yang perlu review, form label manual, dan tombol holdout pindah ke halaman `/labels` yang tidak muncul di sidebar.

Tombol untuk menjalankan ulang pelabelan otomatis tetap tersedia untuk semua akun. Label tombol tidak menyebut nama kamus karena proses ini berjalan diam-diam saat upload.

## 2. Tujuan

1. Menghapus kolom dan konsep role dari aplikasi.
2. Membuat semua akun hasil register setara.
3. Mempertahankan login dan register.
4. Mempertahankan isolasi data per akun.
5. Mempertahankan pelabelan otomatis setelah upload.
6. Memisahkan review dan label manual dari halaman Preprocessing.
7. Membuat halaman `/labels` dapat dipakai semua akun, tetapi tidak ada di sidebar.
8. Menyediakan tombol hitung ulang label otomatis untuk semua akun.
9. Memastikan training dapat diselesaikan tanpa role khusus.

## 3. Bukan Tujuan

1. Tidak mengubah pipeline ML, TF-IDF, SVM, atau evaluasi.
2. Tidak membuat halaman Hasil Klasifikasi baru.
3. Tidak menambah berbagi dataset antar akun.
4. Tidak menghapus login atau register.
5. Tidak mengubah desain visual besar di luar halaman label.
6. Tidak menghapus data komentar atau dataset saat migration.
7. Tidak menambahkan auto-login setelah register. Pengguna tetap diarahkan ke halaman login.

## 4. Anti-Tujuan

1. Halaman `/labels` bukan batas keamanan. URL boleh diketahui, tetapi setiap query tetap dibatasi ke dataset milik akun yang login.
2. Jangan menampilkan istilah `lexicon`, `superadmin`, `admin`, atau `user` di teks antarmuka.
3. Jangan menampilkan baris review atau baris tanpa label di Preprocessing.
4. Jangan mengunci tombol hitung ulang hanya untuk akun tertentu.
5. Jangan membuat label otomatis terlihat seperti label manual.
6. Jangan menyimpan role sebagai string kosong atau nilai tersembunyi. Kolomnya dihapus.

## 5. Pendekatan yang Dipertimbangkan

### A. Hapus kolom role

Kolom `users.role` dihapus. Register tidak mengisi role. Semua akun setara. Ini pilihan yang dipakai karena sesuai permintaan dan tidak menyisakan konsep role.

### B. Pertahankan kolom role, buka semua gate

Kolom tetap ada tetapi tidak dipakai. Ini menyisakan konsep mati dan membingungkan.

### C. Ganti nama role menjadi admin

Semua akun memakai `admin`. Ini masih menyisakan role dan tidak sesuai permintaan terbaru.

## 6. Model Akses

| Hal | Aturan baru |
|---|---|
| Register | Membuat akun tanpa role |
| Login | Memakai akun yang sudah diregister |
| Dataset | Hanya dataset milik akun yang login |
| Komentar | Hanya komentar dari dataset milik akun |
| Review dan label manual | Semua akun, untuk dataset sendiri |
| Holdout | Semua akun, untuk dataset sendiri |
| Training dan testing | Semua akun, untuk model dan dataset sendiri |
| Hitung ulang label otomatis | Semua akun, untuk dataset sendiri |
| Halaman `/labels` | Login, tidak ada di sidebar |
| Metadata label | Terlihat di `/labels`, bukan di Preprocessing |

Halaman `/labels` dapat dibuka dari tautan kecil di Preprocessing. Tautan ini bukan menu sidebar.

## 7. Perubahan Database

1. Kolom `users.role` dihapus dari model `User`.
2. Enum `user_role` dihapus melalui migration.
3. Migration menghapus kolom `role` tanpa mengubah data pengguna lain.
4. Downgrade menambahkan kembali kolom `role` dengan nilai `user`. Ini lossy dan dicatat di migration.
5. `create-superadmin` dihapus. Akun dibuat lewat register.
6. `superadmin_required` dihapus.
7. Route `/admin/health` dihapus.
8. Blueprint `admin_datasets` diganti menjadi blueprint `labels`.

## 8. Route

| Method | Route | Akses | Fungsi |
|---|---|---|---|
| GET | `/labels` | login | Daftar komentar, default filter perlu label |
| POST | `/labels/label` | login | Simpan satu label manual |
| POST | `/labels/label/bulk` | login | Simpan label massal, maksimal 200 |
| POST | `/labels/holdout` | login | Tandai atau lepas holdout |
| GET | `/admin/datasets` | login | Redirect ke `/labels` untuk tautan lama |

Route yang dihapus:

- `/preprocessing/labels/details`
- `/preprocessing/labels/manual`
- `/preprocessing/labels/holdout`
- `/admin/health`

## 9. Aturan Query

### Preprocessing

Hanya baris dengan label akhir:

```sql
sentiment_label IS NOT NULL
AND coalesce(review_status, '') != 'review'
```

Baris tanpa label dan baris `review` tidak muncul. Halaman menampilkan jumlah baris yang menunggu di halaman `/labels`.

Aturan ini hanya berlaku untuk query tampilan. `process_dataset` tetap memproses semua baris, termasuk baris review dan baris tanpa label, agar baris yang dilabeli manual setelah preprocessing sudah punya `cleaned_text`.

Filter yang tersedia:

- semua
- sudah dilabelkan
- positif
- negatif
- netral

### Halaman `/labels`

Semua baris milik dataset. Filter:

- semua
- perlu label
- sudah dilabelkan
- positif
- negatif
- netral
- label manual
- label otomatis

Filter `perlu label` memakai:

```sql
sentiment_label IS NULL OR review_status = 'review'
```

Default halaman adalah `perlu label`.

## 10. Teks Antarmuka

### Tombol hitung ulang

Label tombol:

> Hitung Ulang Label Otomatis

Teks pendamping:

> Label manual yang sudah Anda tetapkan tidak berubah.

Alasan: tombol menyebut tindakan yang terjadi, tidak menyebut nama kamus, dan menjelaskan bahwa keputusan manual tetap aman. Tidak memakai kata "lexicon", "superadmin", "admin", atau "user".

### Halaman label

Judul:

> Review dan Label

Deskripsi:

> Periksa komentar yang belum punya label pasti, lalu tetapkan label manual. Data di halaman ini hanya berasal dari dataset Anda.

Label tautan dari Preprocessing:

> Buka Review dan Label (12)

Angka mengikuti jumlah baris yang perlu label.

### Sidebar

Sidebar hanya berisi:

- Dashboard
- Preprocessing
- Klasifikasi
- Testing
- Logout

Tidak ada menu Review dan Label. Tidak ada menu Kelola Dataset.

### Akun

Blok akun menampilkan nama pengguna dan email. Tidak ada teks role.

## 11. Perubahan Halaman Preprocessing

1. Hapus semua cabang `current_user.role`.
2. Tampilkan tombol hitung ulang untuk semua akun.
3. Hapus kolom Sumber, Skor, Review, Pelabelan manual, dan Data uji independen.
4. Hapus form label manual dan form holdout.
5. Tampilkan jumlah baris yang perlu label dan tautan ke `/labels`.
6. Pertahankan filter label akhir, pencarian, pagination, dan tabel perbandingan teks.
7. Pertahankan progress dialog untuk job pelabelan dan preprocessing.

## 12. Perubahan Halaman Labels

1. Pilih dataset milik akun.
2. Default filter `perlu label`.
3. Tampilkan ringkasan label dan holdout.
4. Tampilkan tabel komentar dengan kolom:
   - komentar
   - label akhir
   - sumber
   - skor
   - status review
   - label manual
   - holdout
5. Form label manual per baris.
6. Form label massal untuk baris terpilih, maksimal 200.
7. Tombol tandai atau lepas holdout.
8. Semua aksi memakai CSRF dan memverifikasi kepemilikan dataset.
9. Halaman tidak muncul di sidebar.

## 13. Perubahan Service

### `comment_query.py`

- Hapus konsep role.
- Tambah parameter `include_review` pada `build_query` dan `paginate`.
- Preprocessing memakai `include_review=False`.
- Halaman labels memakai `include_review=True`.
- `normalize_filter` menerima daftar filter yang diizinkan.
- `pending_review_count` menghitung baris tanpa label atau review.

### `lexicon_service.py`

- Hapus pengecekan role `superadmin`.
- `update_manual_label` tetap memvalidasi label dan pengguna.
- Route tetap memverifikasi kepemilikan komentar.

### `holdout_service.py`

- Hapus pengecekan role `superadmin`.
- Ganti parameter `admin_id` menjadi `user_id`.
- Tetap mensyaratkan label manual yang sah sebelum holdout.

### `datasets.py`

- Hapus larangan impor kolom label manual.
- Semua akun boleh mengimpor label manual untuk dataset sendiri.

## 14. File yang Akan Diubah

- `app/models/__init__.py`
- `app/routes/auth.py`
- `app/routes/datasets.py`
- `app/routes/preprocessing.py`
- `app/routes/labels.py` baru
- `app/routes/admin_datasets.py` dihapus
- `app/services/comment_query.py`
- `app/services/lexicon_service.py`
- `app/services/holdout_service.py`
- `app/templates/base.html`
- `app/templates/preprocessing/index.html`
- `app/templates/labels/index.html` baru
- `app/templates/admin_datasets/index.html` dihapus
- `app/templates/datasets/upload.html` dihapus karena tidak dipakai
- `app/cli.py` dihapus
- `app/__init__.py`
- `migrations/versions/` satu migration baru
- Test terkait role, lexicon, preprocessing, labels, auth, upload, training
- `README.md`
- `docs/ALUR-ROLE.md`
- `STRICT.md` bagian D dan bagian yang menyebut Superadmin
- `AGENT.md` bagian role

## 15. Pengujian

### Auth

- Register membuat akun tanpa role.
- Register tidak menerima role dari request.
- Tidak ada akun baru dengan role `user` atau `superadmin`.
- CLI Superadmin tidak ada.
- Setelah register, pengguna diarahkan ke login.

### Akses

- Semua akun dapat membuka `/labels`.
- Akun tidak dapat membuka dataset akun lain.
- `/labels` tidak muncul di sidebar.
- Preprocessing tidak menampilkan baris review atau baris tanpa label.

### Label

- Label manual tersimpan dan mengubah label akhir.
- Label manual menulis riwayat.
- Label manual tidak ditimpa saat hitung ulang label otomatis.
- Holdout hanya bisa ditandai setelah ada label manual.
- Label massal maksimal 200.
- Filter `perlu label` menampilkan baris review dan baris tanpa label.

### Pipeline

- Upload memicu job pelabelan otomatis.
- Tombol hitung ulang tersedia dan berjalan.
- Preprocessing hanya memproses dataset yang sudah dilabeli.
- Training bisa dijalankan oleh akun biasa setelah holdout tiga kelas.
- Testing single dan batch tetap berjalan.

### Migration

- Database dengan role `user` dan `superadmin` kehilangan kolom role.
- Downgrade mengembalikan kolom role dengan nilai `user`.
- Migration diuji pada database tes.

## 16. Dokumentasi

1. README: hapus tabel role, jelaskan register dan login.
2. `docs/ALUR-ROLE.md`: judul dan isi menjadi alur akses tanpa role.
3. `STRICT.md`: hapus semua aturan yang membedakan Superadmin dan user.
4. `AGENT.md`: hapus instruksi role.
5. `docs/ANALISIS-CODEBASE.md` dan laporan audit lama tidak diubah karena bersifat historis.

## 17. Kriteria Selesai

1. Tidak ada kolom `role` di tabel `users`.
2. Tidak ada teks `superadmin`, `admin`, atau `user` sebagai role di antarmuka dan route aktif.
3. Semua akun hasil register setara.
4. Halaman `/labels` berfungsi dan tidak ada di sidebar.
5. Preprocessing hanya menampilkan komentar berlabel akhir.
6. Hitung ulang label otomatis tersedia untuk semua akun.
7. Label manual tidak ditimpa.
8. Holdout dan training bisa diselesaikan tanpa role khusus.
9. `pytest` lulus.
10. Migration diuji pada database dengan role lama.
11. README dan dokumen alur sudah sesuai konsep baru.

## 18. Risiko

1. Keamanan bergantung pada isolasi `user_id`, bukan nama role.
2. Halaman `/labels` tersembunyi dari navigasi, bukan dari akses. Ini disengaja.
3. Migration menghapus kolom role. Downgrade tidak bisa memulihkan role asli.
4. Tautan lama `/admin/datasets` dialihkan, tetapi route API lama dihapus.
5. Jika kamus sentimen tidak tersedia, semua baris masuk halaman label dan harus dilabeli manual.
6. Semua orang dapat mendaftar. Setiap akun hanya melihat datanya sendiri.
