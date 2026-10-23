# BSD & TSD — Panduan Implementasi AI Agent

## Sistem Analisis Sentimen Komentar YouTube terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Support Vector Machine (SVM)

**Stack wajib:** Python Flask, HTML5, CSS3, JavaScript, MySQL, scikit-learn, pandas, dan Sastrawi (untuk stemming Bahasa Indonesia).

**Tujuan dokumen:** Jadikan dokumen ini sebagai instruksi utama untuk AI coding agent ketika merancang, membangun, menguji, atau memperbaiki aplikasi. Ikuti rancangan dan UI yang sudah ada. Jangan mengganti topik, menambah halaman besar yang tidak diminta, atau menyatakan fitur sudah berfungsi jika belum diimplementasikan dan diuji.

---

# BAGIAN A — BUSINESS SOLUTION DESIGN (BSD)

## 1. Latar Belakang dan Tujuan Sistem

Aplikasi web ini digunakan untuk mengolah komentar YouTube yang berkaitan dengan aktivitas pertambangan PT Freeport Indonesia dan mengklasifikasikan sentimennya menjadi tiga kelas: **Positif, Negatif, dan Netral**. Sistem menyediakan alur dari unggah dataset, preprocessing teks, pembobotan TF-IDF, pelatihan model SVM, evaluasi hasil, sampai pengujian komentar baru.

Tujuan bisnis/fungsional:
1. Memudahkan pengguna mengimpor dataset komentar YouTube berformat CSV.
2. Menampilkan informasi dataset dan ringkasan distribusi sentimen.
3. Memperlihatkan hasil preprocessing teks secara transparan.
4. Melatih model SVM menggunakan representasi fitur TF-IDF.
5. Menyajikan metrik evaluasi dan confusion matrix untuk tiga kelas sentimen.
6. Menguji satu komentar secara langsung atau menguji banyak komentar melalui CSV.
7. Menyimpan metadata dataset, proses, dan hasil analisis pada MySQL agar riwayat dapat ditelusuri.

**Batasan ruang lingkup:** Aplikasi hanya berfokus pada analisis sentimen komentar YouTube terhadap aktivitas pertambangan PT Freeport Indonesia. Seluruh istilah, teks UI, contoh data, alur analisis, dan dokumentasi harus konsisten dengan topik tersebut. Jangan mengarang hasil, metrik, jumlah data, atau status model.

## 2. Peran Pengguna dan Hak Akses (RBAC)

Sistem menggunakan dua role: `superadmin` dan `user`. Pemeriksaan hak akses dilakukan di backend Flask pada setiap route yang memerlukan pembatasan; menyembunyikan tombol di frontend saja tidak cukup.

### 2.1 Superadmin
- Mengakses halaman utama, dataset, preprocessing, klasifikasi, evaluasi, dan testing.
- Menjalankan atau memeriksa pelabelan otomatis berbasis lexicon.
- Melakukan pelabelan manual atau memperbaiki label komentar.
- Melihat sumber label (`manual/anotator` atau `lexicon`), skor lexicon, identitas akun pelabel, waktu pelabelan, dan catatan pelabelan.
- Mengelola akun dan role jika fitur pengelolaan akun disediakan.

### 2.2 Pengguna biasa (`user`)
- Login dan logout.
- Mengakses fitur kerja yang diizinkan: dashboard, upload dataset bila diaktifkan, preprocessing, klasifikasi, dan testing.
- Melihat isi komentar, label sentimen akhir, serta hasil analisis yang diizinkan.
- Tidak dapat melakukan atau mengubah pelabelan manual.
- Tidak dapat melihat sumber label, skor lexicon, identitas pelabel, catatan internal, maupun riwayat pelabelan.
- Tidak dapat mengakses endpoint superadmin secara langsung.

### 2.3 Keamanan role
- Role disimpan di database dan dimuat dari session pengguna yang terautentikasi.
- Akun baru secara default menjadi `user`; role `superadmin` tidak boleh bisa dipilih melalui form registrasi publik. Pembuatan superadmin dilakukan melalui proses administrasi yang aman.
- Password disimpan sebagai hash, tidak pernah sebagai teks biasa.
- Informasi sumber label tetap disimpan di database untuk audit meskipun disembunyikan dari UI pengguna biasa.

## 3. Alur Bisnis Utama

1. Pengunjung membuka **Landing Page**.
2. Pengunjung memilih **Mulai Analisis** lalu diarahkan ke Login atau Register.
3. Pengguna yang sudah login membuka aplikasi utama.
4. Pengguna mengunggah dataset CSV melalui halaman **Import Dataset**.
5. Sistem memvalidasi format, ukuran, encoding, serta kolom komentar dan label bila diperlukan.
6. Sistem menampilkan dataset aktif pada **Dashboard**.
7. Pengguna menjalankan tahapan **Preprocessing** dan memeriksa contoh teks sebelum/sesudah diproses.
8. Pengguna membuka **Klasifikasi**, menentukan konfigurasi yang tersedia, lalu menjalankan TF-IDF, split data, pelatihan SVM, dan evaluasi.
9. Sistem menampilkan metrik evaluasi dan confusion matrix 3 × 3.
10. Pengguna membuka **Testing** untuk memasukkan satu komentar atau mengunggah CSV testing.
11. Sistem menampilkan prediksi sentimen dan ringkasan jumlah Positif, Negatif, dan Netral.
12. Pengguna dapat berpindah antarmenu atau logout.

**Aturan alur:** Dataset perlu diunggah terlebih dahulu sebelum Preprocessing atau Klasifikasi dijalankan. Klasifikasi memerlukan label sentimen pada data training. Single testing membutuhkan model yang sudah berhasil dilatih dan disimpan. Tampilkan pesan yang jelas apabila prasyarat belum terpenuhi.

## 4. Kebutuhan Fungsional

| ID | Fitur | Perilaku yang diharapkan |
|---|---|---|
| BSD-01 | Landing Page | Menampilkan judul penelitian, deskripsi singkat, navigasi, dan tombol Mulai Analisis. |
| BSD-02 | Register | Menerima nama, email, dan password; validasi email; password disimpan sebagai hash. |
| BSD-03 | Login/Logout | Memvalidasi akun dan melindungi halaman internal menggunakan session Flask. |
| BSD-04 | Import Dataset | Menerima CSV, memvalidasi kolom, menampilkan hasil import, dan mencatat metadata dataset. |
| BSD-05 | Dashboard | Menampilkan dataset aktif, jumlah komentar, status proses, dan grafik distribusi sentimen bila label tersedia. |
| BSD-06 | Preprocessing | Menjalankan dan menampilkan tahapan pembersihan teks serta perbandingan teks asli dan teks hasil. |
| BSD-07 | Klasifikasi SVM | Menjalankan TF-IDF, pembagian data, pelatihan SVM, dan evaluasi pada data uji. |
| BSD-08 | Evaluasi | Menampilkan accuracy, precision, recall, F1-score, laporan per kelas, dan confusion matrix 3 × 3. |
| BSD-09 | Single Testing | Menerima satu komentar dan menampilkan kelas sentimen hasil prediksi. |
| BSD-10 | Batch Testing | Menerima CSV pengujian, memprediksi setiap baris, dan menampilkan tabel serta ringkasan jumlah kelas. |
| BSD-11 | Validasi dan Pesan | Menampilkan pesan sukses, peringatan, dan kesalahan yang mudah dipahami. |
| BSD-12 | Riwayat | Menyimpan metadata dataset dan eksperimen agar hasil tidak tertukar antarproses. Implementasikan sesuai kebutuhan dan tahap pengerjaan. |
| BSD-13 | Pelabelan Lexicon | Memberi label otomatis awal pada komentar yang belum memiliki label menggunakan kamus sentimen; simpan skor dan sumber label. |
| BSD-14 | Pelabelan Manual Superadmin | Mengizinkan Superadmin memberi/memperbaiki label, dengan pencatatan akun dan waktu; pengguna biasa dilarang. |
| BSD-15 | Privasi Metadata Label | Sumber label dan metadata anotasi ditampilkan hanya kepada Superadmin, bukan pengguna biasa. |

## 5. Batasan dan Asumsi Bisnis

- Dataset utama diimpor dalam format CSV.
- Sistem harus memetakan nama kolom yang dipilih pengguna ke kolom komentar dan, untuk training, kolom label. Jangan mengasumsikan nama kolom selalu sama tanpa menyediakan validasi/pemetaan.
- Label yang diperbolehkan: `Positif`, `Negatif`, dan `Netral`. Normalisasi kapitalisasi/spasi boleh dilakukan, tetapi label di luar kelas tersebut harus ditandai.
- Urutan proses default: **Upload Dataset → Pelabelan Lexicon → Preprocessing → Klasifikasi SVM → Hasil/Evaluasi → Testing**.
- Lexicon hanya memberi label otomatis untuk komentar yang belum memiliki label manual. Label manual yang sudah tersedia harus dipertahankan sebagai label utama.
- Skor lexicon yang nol, konflik, atau tidak meyakinkan harus ditandai untuk ditinjau; jangan otomatis menganggap setiap skor nol sebagai sentimen netral.
- UI pengguna biasa tidak menampilkan sumber label, skor lexicon, identitas pelabel, catatan anotasi, atau waktu pelabelan. Data tersebut tetap tersimpan untuk audit dan hanya boleh diakses Superadmin.
- Karena urutan default menampilkan lexicon sebelum preprocessing utama, layanan lexicon boleh melakukan normalisasi ringan internal untuk pencocokan (misalnya case folding dan normalisasi tanda baca) tanpa menggantikan hasil preprocessing utama yang akan dijalankan setelahnya.
- Data training untuk supervised learning harus memiliki label yang valid.
- Data testing eksternal boleh tidak memiliki label. Jika label aktual tersedia, tampilkan evaluasi testing hanya setelah memastikan kolom label dipetakan dengan benar.
- Dataset dan hasil tiap pengguna tidak boleh tercampur.
- Jangan menyimpan seluruh matriks TF-IDF ke MySQL. Simpan model dan vectorizer sebagai berkas; simpan metadata, label, hasil, dan metrik yang dibutuhkan di MySQL.
- Jangan membuat angka dummy seolah-olah hasil eksperimen asli. Data contoh hanya boleh diberi label “contoh”.

---

# BAGIAN B — TECHNICAL SOLUTION DESIGN (TSD)

## 6. Arsitektur Sistem

Gunakan arsitektur web berlapis sederhana:

```text
Browser Pengguna
  ├── HTML (struktur halaman)
  ├── CSS (gaya visual responsif)
  └── JavaScript (interaksi UI, validasi ringan, grafik, fetch/AJAX bila diperlukan)
          │ HTTP/HTTPS
          ▼
Flask Application (Python)
  ├── Routes / Controllers
  ├── Authentication & Session
  ├── Services (Dataset, Preprocessing, TF-IDF, SVM, Evaluation)
  ├── Validation & Error Handling
  └── ORM/Database Access Layer
       ├── MySQL: akun, metadata dataset, komentar, eksperimen, metrik, batch testing
       └── File storage: dataset CSV dan artefak model/vectorizer
```

### 6.1 Prinsip Arsitektur
- Flask bertanggung jawab atas routing, session, validasi sisi server, orkestrasi preprocessing, model, dan akses database.
- HTML digunakan sebagai template halaman melalui Jinja2.
- CSS menangani layout dan desain visual; JavaScript menangani interaksi browser dan visualisasi.
- MySQL hanya menyimpan data relasional dan metadata. Model SVM serta vectorizer disimpan pada folder artefak yang tidak bisa diakses langsung dari web.
- Pisahkan route dari business logic. Hindari menaruh semua pemrosesan dalam satu file `app.py`.
- Semua pemeriksaan penting harus dilakukan di backend walaupun validasi frontend juga tersedia.

## 7. Panduan UI/UX — Jangan Menyimpang dari Prototype

### 7.1 Gaya Visual
- Platform utama: desktop web, lebar target sekitar 1280–1440 px; tetap dapat digunakan pada layar lebih kecil.
- Gaya minimalis, bersih, monokromatik: hitam, putih, abu-abu/slate, dengan kontras teks yang memadai.
- Jaga konsistensi tipografi, ukuran judul, radius kartu, tombol, jarak, tabel, dan status proses.
- Gunakan ikon seperlunya dan jangan mengganti layout utama secara sepihak.
- Berikan status interaktif yang jelas: loading, berhasil, peringatan, kosong, dan gagal.
- Untuk halaman internal, gunakan **sidebar navigasi** yang konsisten dengan prototype: **Dashboard, Preprocessing, Klasifikasi, Testing, dan Logout**. Fitur Upload Dataset diakses dari Dashboard/aksi upload sesuai prototype.
- Jangan menambahkan menu utama Pelabelan Lexicon ke sidebar. Tahap Lexicon berada di dalam halaman/alur **Preprocessing** sebagai langkah pertama, sebelum kartu/tahapan cleaning. Jangan mengubah identitas visual atau menambah halaman utama baru tanpa persetujuan. Hasil evaluasi tetap berada di halaman Klasifikasi apabila sesuai prototype.

### 7.2 Halaman UI dan Perilaku

#### A. Landing Page
- Header/navbar dengan judul/brand **ANALISIS SENTIMEN KOMENTAR YOUTUBE**.
- Tautan bagian seperti Tentang, Pertambangan, dan Dashboard mengikuti prototype.
- Hero section dengan judul “ANALISIS SENTIMEN”.
- Tampilkan judul penelitian lengkap: “Analisis Sentimen Komentar YouTube terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Algoritma Support Vector Machine”.
- Tombol utama **Mulai Analisis** mengarah ke Login/Register sesuai status autentikasi.

#### B. Login
- Form email dan password.
- Tombol **Masuk**, tautan ke Register, dan pesan validasi yang ringkas.
- Desain minimalis dengan form/card terpusat sebagaimana prototype.

#### C. Register
- Form nama lengkap, email, dan password.
- Tombol **Daftar**, tautan kembali ke Login, serta validasi input.
- Jangan menampilkan password kembali setelah submit atau menyimpannya dalam teks biasa.

#### D. Import Dataset
- Instruksi format CSV dan penjelasan kolom yang wajib tersedia.
- Kartu upload berisi ikon upload, pemilih file, nama file, dan tombol **Import Dataset**.
- Setelah import, tampilkan status, jumlah baris, kolom yang ditemukan, dan kesalahan validasi bila ada.
- Pertahankan tampilan sederhana, bukan wizard baru yang mengubah desain keseluruhan.

#### E. Dashboard
- Sidebar tetap mengikuti prototype: Dashboard, Preprocessing, Klasifikasi, Testing, Logout. Fitur Upload Dataset diakses dari Dashboard atau aksi upload yang sudah ada di prototype.
- Kartu ringkasan: total komentar dataset aktif, nama dataset, status pelabelan/preprocessing/model, serta aksi cepat untuk mengunggah dataset.
- Diagram batang distribusi Positif, Negatif, Netral hanya jika label tersedia.
- Bila data/label belum tersedia, tampilkan empty state yang menjelaskan langkah berikutnya. Jangan isi angka palsu.

#### F. Preprocessing (Lexicon sebagai langkah pertama dalam halaman yang sama)
- Pertahankan halaman dan gaya UI Preprocessing dari prototype. Jangan membuat menu utama sidebar baru untuk Lexicon. Di dalam halaman ini, tampilkan urutan/langkah kerja: **1. Pelabelan Lexicon → 2. Preprocessing teks → tombol Lanjut ke Klasifikasi**.
- **Panel Lexicon:** tampilkan status pemrosesan, pencarian komentar, filter kelas/status bila relevan, tabel komentar dan label sentimen yang dihasilkan, serta ringkasan distribusi kelas. Angka ringkasan harus berasal dari database aktual. Sumber label, skor lexicon, identitas pelabel, catatan, dan waktu pelabelan hanya tampil bagi Superadmin. Pengguna biasa hanya melihat komentar dan label sentimen akhir.
- Lexicon memberi label otomatis hanya pada komentar tanpa label manual. Label manual dari Superadmin/anotator tidak boleh ditimpa. Simpan nilai label lexicon dan label manual secara terpisah agar asal label tetap dapat ditelusuri.
- Komentar yang skornya nol, mengandung negasi, memiliki polaritas campuran, atau tidak cukup bukti ditandai sebagai perlu ditinjau oleh Superadmin; jangan secara buta menetapkannya menjadi Netral.
- **Pelabelan manual:** sediakan kontrol pilih Positif/Netral/Negatif dan tombol Simpan Label hanya untuk Superadmin. Backend Flask harus menolak permintaan dari pengguna biasa meskipun mereka memanggil endpoint secara langsung. Setelah disimpan, catat akun dan waktu perubahan.
- **Preprocessing teks** dilakukan setelah tahap Lexicon: 1) Cleaning, 2) Case Folding, 3) Stopword Removal, 4) Stemming menggunakan Sastrawi. Tokenisasi/normalisasi boleh menjadi subproses di belakang layar sesuai implementasi.
- Tampilkan tabel perbandingan teks asli dan hasil preprocessing. Tombol **Lanjut ke Klasifikasi** aktif jika pelabelan telah dijalankan dan preprocessing selesai, serta data training mempunyai label valid.
- Jangan menghapus kata negasi penting seperti “tidak”, “bukan”, dan “belum” hanya karena ada di daftar stopword. Simpan hasil teks bersih dengan referensi komentar/dataset asal.

#### G. Klasifikasi
- Tetap pada satu halaman dengan rangkuman tahapan: **TF-IDF → Split Data → Training SVM → Evaluasi**.
- Sediakan pilihan konfigurasi yang benar-benar didukung backend, misalnya proporsi split dan kernel. Default dapat berupa 80:20 serta Linear SVM, tetapi jangan mengklaim hasil sebelum proses berjalan.
- Tampilkan progress/status proses, jumlah data yang dipakai, distribusi kelas, dan hasil evaluasi.
- Metrik: Accuracy, Precision, Recall, F1-score; jelaskan rata-rata yang dipakai (macro/weighted) dan tampilkan laporan per kelas.
- Confusion matrix harus berukuran **3 × 3**, dengan urutan kelas konsisten: Negatif, Netral, Positif (atau urutan lain yang dinyatakan jelas dan konsisten).
- Jangan membuat menu Evaluasi terpisah apabila prototype menempatkan hasil evaluasi di halaman Klasifikasi.

#### H. Testing
- Satu halaman berisi dua bagian:
  - **Single Testing:** textarea komentar, tombol **Jalankan Prediksi**, dan label hasil prediksi.
  - **Batch Testing CSV:** file picker, tombol **Upload & Prediksi CSV**, kartu jumlah prediksi per kelas, total data, dan tabel hasil.
- Testing memerlukan model terlatih. Jika artefak model tidak tersedia, tampilkan instruksi agar pengguna menjalankan Klasifikasi terlebih dahulu.
- Validasi ekstensi/isi CSV, encoding, kolom komentar, ukuran file, dan baris kosong.
- Jika file berisi label aktual, evaluasi batch opsional hanya dilakukan setelah kolom label dipetakan; pisahkan label aktual dan prediksi.

## 8. Struktur Folder yang Disarankan

```text
sentiment-analysis-freeport/
├── app/
│   ├── __init__.py             # App factory, konfigurasi, blueprint
│   ├── config.py               # Konfigurasi environment
│   ├── extensions.py           # SQLAlchemy, LoginManager, CSRF bila digunakan
│   ├── models/                 # Model/tabel database
│   ├── routes/
│   │   ├── auth.py             # Login, register, logout
│   │   ├── dashboard.py        # Dashboard
│   │   ├── datasets.py         # Import dan detail dataset
│   │   ├── preprocessing.py    # Proses teks
│   │   ├── classification.py   # Training dan evaluasi
│   │   └── testing.py          # Single/batch prediction
│   ├── services/
│   │   ├── dataset_service.py
│   │   ├── preprocessing_service.py
│   │   ├── tfidf_service.py
│   │   ├── svm_service.py
│   │   └── evaluation_service.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── landing.html
│   │   ├── auth/login.html
│   │   ├── auth/register.html
│   │   ├── dashboard/index.html
│   │   ├── datasets/upload.html
│   │   ├── preprocessing/index.html
│   │   ├── classification/index.html
│   │   └── testing/index.html
│   └── static/
│       ├── css/style.css
│       ├── js/main.js
│       ├── js/dashboard.js
│       └── js/testing.js
├── instance/                   # SQLite tidak digunakan; config lokal bila perlu
├── storage/
│   ├── uploads/                # Dataset upload, dibatasi dari akses publik
│   └── models/                 # Artefak model/vectorizer per eksperimen
├── migrations/                 # Jika menggunakan Flask-Migrate
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

Catatan: folder `storage/` harus dibatasi akses filesystem-nya dan tidak dipetakan sebagai folder static publik. Folder `instance/` boleh dipakai untuk konfigurasi lokal, bukan sebagai pengganti MySQL.

## 9. Rekomendasi Database MySQL

Gunakan MySQL dengan InnoDB, UTF-8 (`utf8mb4`), foreign key, dan timestamp. SQLAlchemy disarankan untuk mengurangi query mentah dan membantu pengelolaan relasi. Nama tabel dan kolom boleh disesuaikan konsisten dengan implementasi.

### 9.1 Tabel `users`
| Kolom | Tipe yang disarankan | Keterangan |
|---|---|---|
| id | BIGINT PK AI | ID akun |
| full_name | VARCHAR(150) | Nama lengkap |
| email | VARCHAR(255) UNIQUE | Email login |
| password_hash | VARCHAR(255) | Hash password, bukan plaintext |
| role | ENUM('superadmin','user') | Hak akses; registrasi publik harus default `user` |
| created_at | DATETIME | Waktu dibuat |
| updated_at | DATETIME | Waktu diperbarui |

### 9.2 Tabel `datasets`
| Kolom | Tipe yang disarankan | Keterangan |
|---|---|---|
| id | BIGINT PK AI | ID dataset |
| user_id | BIGINT FK | Pemilik dataset |
| original_filename | VARCHAR(255) | Nama berkas asli |
| stored_filename | VARCHAR(255) | Nama acak/internal di storage |
| file_path | VARCHAR(500) | Path internal, tidak diekspos sebagai URL |
| row_count | INT | Jumlah baris valid |
| comment_column | VARCHAR(100) | Kolom komentar yang dipilih |
| label_column | VARCHAR(100) NULL | Kolom label, opsional untuk testing |
| dataset_type | ENUM('train','test','unassigned') | Kegunaan dataset |
| status | VARCHAR(30) | uploaded, validated, processed, failed |
| created_at | DATETIME | Waktu import |

### 9.3 Tabel `comments`
| Kolom | Tipe yang disarankan | Keterangan |
|---|---|---|
| id | BIGINT PK AI | ID komentar internal |
| dataset_id | BIGINT FK | Dataset asal |
| row_number | INT | Nomor baris sumber |
| comment_text | TEXT | Komentar asli |
| cleaned_text | TEXT NULL | Teks hasil preprocessing (dibuat setelah lexicon) |
| manual_label | ENUM('Positif','Negatif','Netral') NULL | Label manual yang diisi Superadmin/anotator |
| lexicon_label | ENUM('Positif','Negatif','Netral') NULL | Label otomatis dari lexicon jika dapat ditentukan |
| lexicon_score | DECIMAL(10,6) NULL | Skor lexicon untuk kebutuhan Superadmin/audit |
| sentiment_label | ENUM('Positif','Negatif','Netral') NULL | Label akhir: manual jika tersedia, jika tidak gunakan label lexicon yang lolos aturan |
| label_source | ENUM('manual','lexicon','review') NULL | Asal/status label; jangan ditampilkan ke user biasa |
| labeled_by | BIGINT NULL FK users.id | Akun Superadmin yang melakukan pelabelan manual |
| labeled_at | DATETIME NULL | Waktu pelabelan manual terakhir |
| label_note | VARCHAR(500) NULL | Catatan internal pelabelan, khusus Superadmin |
| created_at | DATETIME | Waktu disimpan |

Tambahkan unique constraint pada kombinasi `(dataset_id, row_number)` untuk menghindari impor baris ganda dalam dataset yang sama. Apabila ada username, tanggal, atau jumlah likes, simpan hanya jika kolom tersebut memang tersedia dan dibutuhkan.

### 9.4 Tabel `model_runs`
| Kolom | Tipe yang disarankan | Keterangan |
|---|---|---|
| id | BIGINT PK AI | ID eksperimen |
| user_id | BIGINT FK | Pemilik eksperimen |
| dataset_id | BIGINT FK | Dataset training |
| experiment_name | VARCHAR(150) | Nama eksperimen |
| split_ratio | VARCHAR(20) | Contoh `80:20` |
| random_state | INT | Seed untuk reproduksibilitas |
| vectorizer_config | JSON NULL | Parameter TF-IDF yang digunakan |
| svm_config | JSON NULL | Kernel, C, dan parameter terkait |
| accuracy | DECIMAL(8,6) NULL | Akurasi pada data uji |
| precision_macro | DECIMAL(8,6) NULL | Macro precision |
| recall_macro | DECIMAL(8,6) NULL | Macro recall |
| f1_macro | DECIMAL(8,6) NULL | Macro F1 |
| classification_report | JSON NULL | Metrik per kelas |
| confusion_matrix | JSON NULL | Matriks 3 × 3 |
| model_path | VARCHAR(500) NULL | Path model artefak internal |
| vectorizer_path | VARCHAR(500) NULL | Path vectorizer internal |
| status | VARCHAR(30) | queued, running, completed, failed |
| created_at | DATETIME | Waktu eksperimen |

### 9.5 Tabel `predictions` (single dan batch testing)
| Kolom | Tipe yang disarankan | Keterangan |
|---|---|---|
| id | BIGINT PK AI | ID prediksi |
| user_id | BIGINT FK | Pengguna pemilik prediksi |
| model_run_id | BIGINT FK | Model yang digunakan |
| batch_id | BIGINT NULL | ID batch jika berasal dari CSV |
| input_text | TEXT | Komentar yang diuji |
| predicted_label | ENUM('Positif','Negatif','Netral') | Hasil prediksi |
| actual_label | ENUM('Positif','Negatif','Netral') NULL | Label aktual jika disediakan |
| row_number | INT NULL | Baris pada file batch |
| created_at | DATETIME | Waktu prediksi |

Jika fitur batch membutuhkan ringkasan terpisah, tambahkan tabel `prediction_batches` berisi pemilik, nama berkas, jumlah baris, status, dan waktu. Jangan menambah tabel berlebihan jika penyimpanan batch dapat ditangani secara konsisten dengan desain yang lebih sederhana.

### 9.6 Relasi inti

```text
users 1 ─── N datasets
users 1 ─── N model_runs
users 1 ─── N predictions
datasets 1 ─── N comments
datasets 1 ─── N model_runs
model_runs 1 ─── N predictions
prediction_batches 1 ─── N predictions  (bila tabel batch digunakan)
```

### 9.7 Ketentuan penyimpanan
- Jangan simpan password asli.
- Jangan menyimpan data TF-IDF dalam kolom MySQL sebagai satu matriks besar.
- Simpan `TfidfVectorizer` dan model SVM dengan `joblib` pada storage privat. Catat path serta metadata eksperimen di MySQL.
- Batasi akses setiap dataset dan eksperimen berdasarkan `user_id` jika pengguna memiliki data masing-masing.
- Jangan menyimpan path yang berasal langsung dari input pengguna tanpa validasi; buat nama berkas internal yang aman.

## 10. Rancangan Route Flask

Route boleh diimplementasikan sebagai Blueprint. Berikut kontrak awal yang perlu dijaga konsisten dengan form dan JavaScript.

| Method | Route | Fungsi | Akses |
|---|---|---|---|
| GET | `/` | Landing Page | Publik |
| GET, POST | `/login` | Login pengguna | Publik |
| GET, POST | `/register` | Registrasi akun | Publik |
| POST | `/logout` | Logout dan hapus session | Login |
| GET | `/dashboard` | Ringkasan dataset dan hasil | Login |
| GET, POST | `/datasets/upload` | Form dan import CSV | Login |
| GET | `/datasets/<id>` | Informasi dataset | Pemilik dataset |
| GET | `/preprocessing` | Halaman preprocessing yang memuat langkah Lexicon terlebih dahulu lalu tahapan preprocessing teks | Login |
| POST | `/preprocessing/lexicon/run` | Memberi label lexicon pada komentar yang belum memiliki label manual | Login |
| POST | `/preprocessing/labels/manual` | Menyimpan/memperbarui label manual dan metadata anotasi | **Superadmin saja** |
| GET | `/preprocessing/labels/details` | Mengambil detail sumber/skor/metadata label | **Superadmin saja** |
| POST | `/preprocessing/run` | Menjalankan preprocessing teks setelah tahap lexicon | Login |
| GET | `/classification` | Halaman klasifikasi | Login |
| POST | `/classification/train` | TF-IDF, split, training, dan evaluasi | Login |
| GET | `/testing` | Halaman single/batch testing | Login |
| GET, POST | `/admin/users` | Pengelolaan akun/role bila diperlukan | **Superadmin saja** |
| POST | `/testing/single` | Prediksi satu komentar | Login |
| POST | `/testing/batch` | Upload CSV dan prediksi massal | Login |
| GET | `/testing/batch/<id>/results` | Melihat hasil batch | Pemilik batch |

Gunakan redirect-GET-POST untuk form standar. JSON response dapat dipakai untuk interaksi JavaScript, dengan format yang konsisten seperti `success`, `message`, dan `data`. Jangan menerima `user_id` dari frontend untuk menentukan kepemilikan; ambil identitas pengguna dari session login.

## 11. Rancangan Pipeline NLP dan Machine Learning

### 11.1 Validasi Dataset
1. Pastikan file CSV benar-benar CSV dan ukuran file di bawah batas konfigurasi.
2. Baca dengan encoding yang sesuai; tangani UTF-8/UTF-8-SIG dan tampilkan pesan jika gagal.
3. Validasi kolom komentar. Untuk training, pastikan kolom label tersedia.
4. Periksa baris kosong, duplikat, nilai label di luar Positif/Negatif/Netral, serta jumlah data tiap kelas.
5. Jangan melanjutkan training jika data atau kelas tidak memenuhi persyaratan yang dibutuhkan.

### 11.2 Pelabelan Lexicon (sebelum preprocessing utama)
1. Jalankan tahap ini setelah dataset berhasil divalidasi dan diimpor.
2. Untuk komentar yang sudah mempunyai `manual_label`, pertahankan label manual tersebut sebagai label utama; jangan menimpanya dengan hasil lexicon.
3. Untuk komentar tanpa label manual, lakukan pencocokan menggunakan kamus sentimen Bahasa Indonesia/lexicon yang digunakan dan dicatat versinya. Normalisasi ringan internal (misalnya huruf kecil dan tanda baca) boleh dilakukan agar pencocokan konsisten; tahapan ini tidak menggantikan preprocessing utama.
4. Simpan `lexicon_score` dan `lexicon_label` terpisah. Skor nol bukan bukti yang cukup untuk menyimpulkan Netral; status tak meyakinkan, konflik polaritas, dan negasi harus diarahkan ke `review`.
5. Terapkan penanganan negasi dan frasa agar contoh seperti “tidak merusak” tidak otomatis diputuskan sebagai negatif hanya karena memuat kata “merusak”. Lexicon perlu divalidasi terhadap komentar aktual topik aktivitas pertambangan PT Freeport Indonesia.
6. Label akhir ditentukan dengan aturan eksplisit: label manual mengungguli label lexicon; jika tidak ada label manual, gunakan label lexicon yang memenuhi aturan keyakinan/kualitas; jika tidak, tandai perlu review dan jangan memaksakan kelas.
7. Simpan sumber label, skor lexicon, waktu, dan identitas pelabel untuk audit. Metadata internal hanya boleh dikirim kepada Superadmin.
8. Untuk evaluasi SVM yang dapat dipertanggungjawabkan, sisihkan data uji berlabel manual yang tidak dipakai saat training atau penyetelan model. Jangan mengevaluasi model hanya dengan label lexicon yang sama-sama dihasilkan oleh aturan lexicon lalu mengklaimnya sebagai ground truth independen.

### 11.3 Preprocessing

Jalankan pada komentar dengan alur yang konsisten dan terdokumentasi:
1. **Cleaning:** normalisasi URL, mention, hashtag, karakter khusus dan tanda baca sesuai aturan yang dipilih. Jangan membuang informasi sentimen yang bermakna tanpa evaluasi.
2. **Case folding:** ubah huruf menjadi huruf kecil.
3. **Tokenisasi:** pecah teks menjadi token sesuai implementasi.
4. **Normalisasi:** gunakan kamus slang jika tersedia dan dapat dipertanggungjawabkan; jangan membuat pemetaan kata otomatis yang tidak tervalidasi.
5. **Stopword removal:** gunakan daftar stopword Bahasa Indonesia yang dapat ditinjau. Pertahankan negasi yang penting seperti `tidak`, `bukan`, dan `belum`.
6. **Stemming:** gunakan Sastrawi bila sesuai untuk mengubah kata berimbuhan menjadi kata dasar.

UI utama tetap memperlihatkan empat kelompok: Cleaning, Case Folding, Stopword Removal, Stemming. Tahapan tokenisasi/normalisasi dapat ditampilkan sebagai detail/subproses tanpa mengubah layout utama kecuali pemilik proyek meminta.

### 11.4 TF-IDF dan Pembagian Data
- Pisahkan data training dan testing dengan `train_test_split` serta `random_state` tetap agar hasil dapat direproduksi.
- Gunakan stratifikasi (`stratify=y`) jika jumlah data kelas memungkinkan.
- **Hindari data leakage:** bagi data dahulu, fit `TfidfVectorizer` hanya pada teks training, lalu transform teks testing menggunakan vectorizer yang sama.
- Jangan fit ulang vectorizer pada test data.
- Catat parameter vectorizer, split ratio, random state, dan jumlah data untuk setiap eksperimen.

### 11.5 Training SVM
- Implementasikan `sklearn.svm.SVC` atau classifier SVM yang disetujui oleh pemilik proyek.
- Default awal yang disarankan: kernel `linear` dengan nilai `C` yang eksplisit dan tercatat; nilai dapat diubah melalui konfigurasi yang memang tersedia di UI.
- Karena sentimen memiliki tiga kelas, pastikan strategi multiclass dari implementasi dipahami serta dinyatakan di laporan.
- Jangan mengklaim probabilitas keyakinan prediksi kecuali `probability=True` telah dipakai dan model sudah sesuai. Label sentimen saja sudah cukup untuk versi awal.
- Simpan model dan vectorizer bersama-sama sebagai artefak eksperimen yang saling cocok. Cegah model dari satu eksperimen dipasangkan dengan vectorizer dari eksperimen lain.

### 11.6 Evaluasi
- Evaluasi pada data testing yang tidak dipakai untuk fit vectorizer atau melatih model.
- Hitung accuracy, precision, recall, dan F1-score.
- Tampilkan precision/recall/F1 per kelas dan jelaskan agregat macro atau weighted. Untuk membandingkan tiga kelas, utamakan agar metrik per kelas dan macro average sama-sama terlihat.
- Confusion matrix wajib berukuran 3 × 3 dengan label sumbu aktual dan prediksi yang jelas.
- Simpan hasil eksperimen dan konfigurasi agar dapat ditinjau kembali.
- Jika kelas terlalu sedikit atau pembagian stratified gagal, tampilkan alasan dan minta penyesuaian; jangan menyembunyikan kegagalan dengan metrik buatan.

## 12. Keamanan dan Keandalan

- Simpan secret key dan kredensial MySQL dalam environment variables; sertakan `.env.example` tanpa rahasia sebenarnya.
- Gunakan `werkzeug.security` untuk hash dan verifikasi password.
- Proteksi halaman privat dengan autentikasi dan otorisasi per pemilik resource.
- Terapkan dekorator/pengecekan role untuk setiap route Superadmin. Backend wajib melarang user biasa mengakses endpoint pelabelan manual dan endpoint metadata sumber label.
- Jangan kirim `manual_label`, `label_source`, `lexicon_score`, `labeled_by`, `labeled_at`, atau `label_note` ke template/API pengguna biasa. Jangan mengandalkan CSS/JavaScript sebagai satu-satunya lapisan pembatasan.
- Terapkan CSRF protection untuk form yang menggunakan session/cookie.
- Validasi nama file, MIME/ekstensi, ukuran unggahan, kolom, dan isi CSV di server.
- Jangan menggabungkan path file dari input pengguna secara langsung. Buat nama berkas aman dan acak.
- Jangan menampilkan traceback, password, connection string, atau path internal pada pesan ke pengguna.
- Gunakan parameterized query/ORM untuk mencegah SQL injection.
- Atur batas ukuran request dan tangani kegagalan database/model dengan pesan yang tidak membocorkan detail sensitif.
- Jangan menghapus atau menimpa dataset/model yang masih direferensikan eksperimen tanpa pengecekan dependensi.

## 13. Non-Functional Requirements

- **Usability:** alur kerja mudah diikuti; tombol dinonaktifkan saat proses yang sama sedang berlangsung.
- **Consistency:** komponen visual dan navigasi konsisten dengan prototype.
- **Maintainability:** route, service ML, model database, template, CSS, dan JavaScript dipisahkan.
- **Reproducibility:** konfigurasi eksperimen dan random seed disimpan.
- **Performance:** untuk data berukuran besar, hindari membaca/mengirim semua komentar sekaligus ke browser; gunakan pagination dan proses batch yang dibatasi.
- **Accessibility:** label input jelas, status tidak hanya dibedakan dengan warna, tabel dapat dibaca, dan fokus keyboard terlihat.
- **Error recovery:** kegagalan import/training/testing tidak boleh meninggalkan status seolah proses sukses.

## 14. Kriteria Penerimaan (Acceptance Criteria)

1. Pengguna dapat register, login, dan logout tanpa menyimpan password plaintext.
2. Pengguna dapat mengunggah CSV valid dan memperoleh ringkasan jumlah baris serta kolom.
3. CSV salah format atau kehilangan kolom penting ditolak dengan pesan yang informatif.
4. Dataset training tanpa label tidak dapat digunakan untuk supervised training.
5. Pada halaman Preprocessing, pelabelan Lexicon berjalan sebagai langkah pertama sebelum preprocessing teks; menu utama sidebar tidak berubah dari prototype.
6. Label manual yang sudah tersedia tidak pernah ditimpa oleh lexicon; komentar yang tidak meyakinkan ditandai untuk review.
7. Hanya Superadmin yang dapat mengubah label manual dan melihat metadata sumber label; endpoint backend menolak pengguna biasa.
8. Halaman Preprocessing memperlihatkan teks asli dan teks yang sudah diproses.
9. Klasifikasi menggunakan data training dan testing terpisah; vectorizer hanya di-fit pada training.
10. Sistem menyimpan artefak model/vectorizer dan metadata eksperimen secara konsisten.
11. Evaluasi menampilkan empat metrik yang diminta dan confusion matrix 3 × 3.
12. Single testing tidak berjalan jika belum ada model yang berhasil dilatih.
13. Batch testing menghasilkan satu prediksi untuk setiap baris komentar valid dan menyediakan tabel/ringkasan kelas.
14. Dashboard tidak menampilkan angka palsu saat dataset atau hasil belum tersedia.
15. Menu dan layout mengikuti prototype: Landing Page, Login, Register, Import Dataset melalui aksi dashboard, Dashboard, Preprocessing, Klasifikasi, Testing. Tahap Lexicon berada di dalam halaman Preprocessing; jangan membuat menu utama baru.
16. Resource pengguna tidak dapat diakses oleh pengguna lain melalui perubahan ID pada URL.
17. Semua route utama, validasi, error state, dan alur UI diuji sebelum fitur dinyatakan selesai.

## 15. Instruksi Kerja untuk AI Coding Agent

Saat mengerjakan repositori:

1. **Audit dahulu** struktur folder, dependency, database, halaman, gambar prototype, dan fitur yang sudah ada. Jangan menimpa implementasi yang berfungsi tanpa alasan.
2. Jadikan UI prototype sebagai acuan. Pertahankan posisi komponen, sidebar, kartu ringkasan, bentuk form, warna monokromatik, dan hirarki visual sejauh aset tersedia.
3. Pastikan seluruh UI, data contoh, label, penjelasan, dan dokumentasi hanya membahas aktivitas pertambangan PT Freeport Indonesia.
4. Implementasikan backend Flask, frontend HTML/CSS/JS, dan MySQL dengan pemisahan tanggung jawab yang jelas.
5. Gunakan konfigurasi `.env`; jangan menaruh kredensial dalam source code.
6. Utamakan fitur secara bertahap: autentikasi dan role → import dataset → dashboard → pelabelan Lexicon di dalam halaman Preprocessing → preprocessing teks → klasifikasi/evaluasi → single/batch testing.
7. Jangan menambahkan menu utama Lexicon ke sidebar; tahap Lexicon menjadi langkah pertama di halaman Preprocessing agar UI tetap sesuai PRD awal.
8. Jangan menimpa label manual dengan label lexicon. Metadata sumber label hanya dikirim ke UI/API Superadmin; blokir endpoint tersebut untuk pengguna biasa.
9. Jangan mengarang hasil eksperimen atau mengisi dashboard dengan data statis yang terlihat seperti data nyata. Gunakan empty state jika data belum ada.
10. Beri validasi sisi frontend dan backend. Pesan kesalahan harus menjelaskan tindakan yang dapat dilakukan pengguna.
11. Buat migration/schema database dan petunjuk setup yang dapat diulang.
12. Tambahkan pengujian minimal untuk login, role, validasi CSV, lexicon, akses pelabelan manual, preprocessing, training/evaluasi tiga kelas, single testing, dan batch testing.
13. Setelah perubahan, laporkan file yang diubah, fitur yang selesai, cara menjalankan aplikasi, konfigurasi database, cara menjalankan migration, hasil pengujian, dan keterbatasan yang belum diselesaikan.
14. Jangan mengklaim aplikasi telah terhubung ke MySQL atau model telah terlatih sebelum menjalankan dan memverifikasi prosesnya.

## 16. Setup dan Konfigurasi yang Perlu Disediakan

Sediakan `.env.example` dengan placeholder, misalnya:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/sentiment_freeport
UPLOAD_FOLDER=storage/uploads
MODEL_FOLDER=storage/models
MAX_CONTENT_LENGTH=16777216
```

Jangan masukkan kredensial sungguhan ke repositori. `FLASK_ENV` dapat berbeda sesuai versi Flask; utamakan konfigurasi debug melalui pengaturan yang sesuai versi yang digunakan.

Dependensi inti yang biasanya dibutuhkan:
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF (untuk CSRF/form jika digunakan)
- Flask-Migrate
- PyMySQL
- pandas
- scikit-learn
- Sastrawi
- joblib
- python-dotenv

Pilih versi yang saling kompatibel, pin versi dalam `requirements.txt`, dan dokumentasikan versi Python serta MySQL yang benar-benar digunakan.

---

# Prinsip Final

**Implementasikan sesuai kebutuhan dan prototype, bukan hanya membuat tampilan yang terlihat selesai.** Setiap tombol harus memiliki perilaku yang jelas; setiap metrik harus berasal dari proses yang benar-benar dijalankan; setiap data harus dapat ditelusuri ke dataset/eksperimen asal; dan UI tidak boleh menyatakan proses berhasil sebelum backend mengonfirmasikannya.
