# AGENT.md — Urutan Eksekusi AI Coding Agent

## 1. Identitas Proyek

**Nama aplikasi:** Sistem Analisis Sentimen Komentar YouTube terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Algoritma Support Vector Machine (SVM).

**Stack utama:** Python Flask, HTML5, CSS3, JavaScript, MySQL, pandas, scikit-learn, dan Sastrawi.

**Dokumen acuan:**
1. `PRD` — kebutuhan produk dan referensi layar.
2. `BSD/TSD` — aturan bisnis, arsitektur, alur data, desain database, keamanan, dan kriteria penerimaan.
3. Prototype/screenshot UI yang disediakan pemilik proyek — acuan visual utama.
4. `STRICT.md` — aturan wajib yang tidak boleh dilanggar.

Jika ada ketidaksesuaian, prioritaskan batasan studi kasus dan aturan pada `STRICT.md`, kemudian BSD/TSD terbaru. PRD awal merupakan acuan visual dan kebutuhan layar, bukan izin untuk mengaktifkan studi kasus lain.

---

## 2. Tujuan Tugas Agent

Bangun aplikasi web yang berfungsi untuk mengunggah dataset komentar YouTube, memberi label awal menggunakan lexicon pada komentar yang belum memiliki label manual, melakukan preprocessing, melatih dan mengevaluasi SVM, serta menguji komentar baru. Terapkan autentikasi dan otorisasi role Superadmin/User. Simpan data terstruktur di MySQL dan artefak model/vectorizer di penyimpanan file privat.

**Jangan langsung menulis ulang seluruh proyek.** Audit dahulu repositori, identifikasi komponen yang sudah berjalan, lalu kerjakan per tahap dengan pengujian setelah setiap tahap.

---

## 3. Urutan Eksekusi Wajib

### Tahap 0 — Audit repositori dan acuan

1. Periksa struktur folder, file dependency, konfigurasi, model database, route, template HTML, CSS, JavaScript, aset UI, dan pengujian yang sudah ada.
2. Periksa apakah Flask dan MySQL sudah terhubung, apakah autentikasi sudah ada, serta apakah ada layanan preprocessing/SVM yang dapat digunakan ulang.
3. Baca `PRD`, `BSD/TSD`, dan `STRICT.md` sebelum melakukan perubahan.
4. Catat kondisi awal: fitur yang sudah berjalan, belum berjalan, gagal, atau belum dapat diverifikasi.
5. Jangan menghapus atau mengganti file yang ada hanya karena ingin merapikan struktur. Berikan alasan teknis sebelum refactor besar.

**Gerbang selesai tahap 0:** ada ringkasan audit, daftar gap, rencana file yang akan dibuat/diubah, dan cara menjalankan proyek yang ditemukan. Belum boleh mengklaim fitur berfungsi tanpa pengujian.

### Tahap 1 — Fondasi aplikasi dan konfigurasi

1. Pastikan aplikasi menggunakan Flask dengan pola modular/App Factory jika sesuai kondisi repositori.
2. Pisahkan route/controller dari business logic/services.
3. Siapkan konfigurasi berbasis environment variables dan `.env.example` tanpa kredensial asli.
4. Siapkan koneksi MySQL, ORM/migration jika dipakai, penanganan error, logging dasar, dan konfigurasi upload.
5. Buat `README.md` yang memuat persyaratan, konfigurasi, setup database, migration/schema, serta perintah menjalankan aplikasi.
6. Pastikan folder upload dan folder artefak model tidak dapat diakses langsung sebagai folder publik/static.

**Gerbang selesai tahap 1:** aplikasi Flask dapat dijalankan dengan konfigurasi lokal, koneksi MySQL dapat diuji, dan kegagalan konfigurasi menghasilkan pesan yang aman serta jelas.

### Tahap 2 — Skema database dan autentikasi/RBAC

1. Siapkan tabel yang diperlukan, minimal mencakup pengguna, dataset, komentar, hasil pelabelan/metadata label, eksperimen model, dan prediksi/testing. Sesuaikan dengan skema BSD/TSD.
2. Gunakan primary key, foreign key, indeks yang diperlukan, timestamp, dan `utf8mb4`.
3. Terapkan register, login, logout, hashing password, session aman, validasi input, dan proteksi CSRF untuk form berbasis session.
4. Role yang didukung: `superadmin` dan `user`.
5. Registrasi publik harus selalu menetapkan role `user`; jangan menerima role dari input register. Pembuatan Superadmin dilakukan melalui mekanisme administrasi aman.
6. Buat pemeriksaan otorisasi backend untuk setiap route/endpoint yang dibatasi.
7. Isolasi data berdasarkan pemilik atau izin yang memang ditetapkan; jangan menganggap ID pada URL sebagai bukti hak akses.

**Gerbang selesai tahap 2:** pengujian login/logout/register berhasil, password tersimpan sebagai hash, dan user biasa tidak dapat mengakses endpoint Superadmin secara langsung.

### Tahap 3 — Implementasi UI dasar sesuai prototype

1. Pertahankan identitas visual PRD/prototype: minimalis, monokromatik hitam-putih-abu-abu/slate, kontras jelas, dan fokus desktop 1280–1440 px.
2. Buat atau pertahankan halaman: Landing Page, Login, Register, Import Dataset, Dashboard, Preprocessing, Klasifikasi, dan Testing.
3. Untuk halaman kerja, pertahankan sidebar prototype: Dashboard, Preprocessing, Klasifikasi, Testing, dan Logout. Import Dataset tetap dapat diakses dari aksi upload yang ada pada Dashboard/prototype.
4. **Jangan menambahkan menu utama Lexicon di sidebar.** Tahap Lexicon ditempatkan sebagai langkah pertama di dalam halaman Preprocessing.
5. Jangan mengganti tata letak, palet warna, hierarki visual, atau bentuk form secara sepihak jika prototype tersedia.
6. Setiap halaman harus menyediakan status loading, sukses, empty state, validasi, dan error state yang konsisten.
7. Hindari angka metrik statis yang terlihat seperti hasil nyata. Gunakan data MySQL aktual atau empty state.

**Gerbang selesai tahap 3:** semua halaman utama dapat dirender dan navigasi sesuai prototype. Data placeholder harus diberi label jelas sebagai contoh atau tidak digunakan.

### Tahap 4 — Import dan validasi dataset CSV

1. Izinkan upload CSV saja, dengan batas ukuran file yang dikonfigurasi.
2. Validasi sisi server: ukuran, ekstensi, encoding, isi CSV, kolom komentar, nilai kosong, dan kolom label jika ada.
3. Sediakan pemetaan kolom komentar dan label bila nama kolom dataset tidak baku.
4. Simpan file dalam nama internal yang aman, metadata dataset di MySQL, serta catat pengguna dan waktu upload.
5. Simpan data komentar dengan relasi ke dataset; cegah pencampuran antar-dataset.
6. Tampilkan total baris yang berhasil dibaca, jumlah baris yang ditolak/diabaikan, kolom terdeteksi, dan alasan validasi. Semua angka wajib berasal dari proses import aktual.
7. Cegah unggahan ulang atau perubahan dataset secara tidak sengaja. Jika ada deduplikasi, jelaskan aturan dan catat jumlah yang dihapus.

**Gerbang selesai tahap 4:** CSV valid dapat diimpor, CSV invalid ditolak dengan pesan yang informatif, dan data yang ditampilkan cocok dengan isi berkas.

### Tahap 5 — Pelabelan Lexicon sebagai langkah pertama Preprocessing

1. Implementasikan layanan lexicon yang terpisah dari route dan UI.
2. Jalankan lexicon sebelum preprocessing utama, sesuai urutan produk:
   **Upload Dataset → Pelabelan Lexicon → Preprocessing → Klasifikasi SVM → Hasil/Evaluasi → Testing.**
3. Lexicon hanya memberi label otomatis pada komentar yang belum mempunyai label manual yang sah.
4. Pertahankan label manual sebagai label utama. Jangan menimpa atau menghapusnya ketika lexicon berjalan.
5. Simpan label lexicon, skor, versi/sumber kamus, status review, dan waktu pemrosesan secara terpisah dari label manual.
6. Gunakan normalisasi ringan internal untuk pencocokan lexicon bila perlu. Tahap ini tidak boleh menggantikan hasil preprocessing utama.
7. Perlakukan komentar dengan skor nol, konflik polaritas, negasi, sarkasme, atau bukti lemah sebagai perlu review bila aturan lexicon tidak cukup untuk menentukan kelas. Jangan otomatis menyamakan skor nol dengan Netral.
8. Hanya Superadmin dapat mengakses metadata sumber label, skor, identitas pelabel, catatan, dan melakukan pelabelan/koreksi manual.
9. User biasa hanya melihat komentar dan label akhir sesuai izin. Batasi data pada backend; jangan sekadar menyembunyikan kolom dengan CSS/JavaScript.
10. Sediakan filter, pencarian, pagination, ringkasan label, tabel hasil, dan tombol **Lanjut ke Preprocessing** di dalam halaman yang sama dan tetap mengikuti prototype.
11. Jangan menggunakan angka contoh sebagai statistik aktual. Jika lexicon belum dijalankan, tampilkan status belum diproses.

**Gerbang selesai tahap 5:** label manual tetap tidak berubah setelah lexicon dijalankan; data tanpa label diproses; komentar meragukan ditandai untuk review; metadata sensitif hanya dapat diakses Superadmin.

### Tahap 6 — Preprocessing teks

Jalankan setelah tahap lexicon. Tampilkan empat kelompok utama pada UI:

1. Cleaning.
2. Case Folding.
3. Stopword Removal.
4. Stemming dengan Sastrawi.

Tokenisasi dan normalisasi dapat menjadi subproses internal atau detail tambahan jika tidak merombak desain utama.

Ketentuan:
- Simpan teks asli dan teks hasil preprocessing secara terpisah.
- Pertahankan relasi ke komentar dan dataset asal.
- Jangan membuang negasi penting seperti `tidak`, `bukan`, dan `belum` secara membabi buta.
- Terapkan transformasi yang konsisten pada training, testing, single testing, dan batch testing.
- Tampilkan tabel perbandingan komentar asli dan hasil preprocessing.

**Gerbang selesai tahap 6:** hasil transformasi dapat diperiksa, data kosong/duplikat ditangani dengan aturan yang jelas, dan pemrosesan yang sama digunakan untuk data training maupun inference.

### Tahap 7 — Klasifikasi TF-IDF dan SVM

1. Pastikan dataset training mempunyai label valid `Positif`, `Negatif`, atau `Netral`.
2. Sisihkan test set sebelum `fit` vectorizer. Gunakan `train_test_split`, `random_state` tetap, dan `stratify` bila ukuran kelas memungkinkan.
3. Fit `TfidfVectorizer` hanya pada teks training; transform teks test dengan vectorizer yang sama. Jangan fit vectorizer pada test set.
4. Implementasikan SVM menggunakan scikit-learn. Gunakan konfigurasi yang tercatat, dengan default yang eksplisit (misalnya kernel linear) dan jangan menyatakan konfigurasi sudah dipakai jika belum.
5. Simpan split ratio, random state, parameter vectorizer, parameter SVM, waktu, jumlah data, dan hasil eksperimen.
6. Simpan model dan vectorizer sebagai pasangan artefak di storage privat; pastikan ID eksperimen dan versinya saling cocok.
7. Jika kelas terlalu sedikit atau training gagal, tampilkan error yang dapat ditindaklanjuti; jangan membuat hasil pengganti.

**Gerbang selesai tahap 7:** model bisa dilatih dari data valid, artefak model/vectorizer dapat dimuat kembali, dan alur training bebas dari kebocoran data TF-IDF.

### Tahap 8 — Evaluasi dan visualisasi

1. Evaluasi hanya menggunakan test set yang tidak digunakan untuk melatih model maupun fit vectorizer.
2. Hitung Accuracy, Precision, Recall, F1-score, metrik per kelas, dan macro/weighted average yang disebutkan secara eksplisit.
3. Confusion matrix wajib berukuran 3 × 3; tampilkan nama kelas dan sumbu aktual/prediksi dengan jelas.
4. Simpan hasil evaluasi dengan referensi ke eksperimen.
5. Tampilkan hasil evaluasi di halaman Klasifikasi sesuai prototype; jangan menambah halaman utama Evaluasi terpisah.
6. Jika evaluasi belum dijalankan, tampilkan empty state, bukan nilai nol atau angka dummy yang dapat disalahartikan sebagai hasil.

**Gerbang selesai tahap 8:** metrik UI cocok dengan hasil backend yang dihitung ulang pada eksperimen yang sama.

### Tahap 9 — Testing single dan batch

**Single testing**
1. Terima komentar baru melalui textarea.
2. Periksa bahwa model dan vectorizer yang kompatibel tersedia.
3. Terapkan preprocessing yang sama dengan pipeline training.
4. Transform teks dengan vectorizer yang tersimpan, kemudian prediksi dengan model yang cocok.
5. Tampilkan label hasil dan pesan yang jelas jika komentar kosong/model belum tersedia.

**Batch testing**
1. Terima CSV terpisah dan validasi kolom komentar, encoding, ukuran, dan baris kosong.
2. Terapkan pipeline preprocessing dan inferensi yang sama.
3. Tampilkan total valid, gagal, prediksi Positif/Netral/Negatif, serta tabel prediksi.
4. Jika label aktual tersedia dan terpetakan, evaluasi tambahan boleh dilakukan; pisahkan label aktual dari hasil prediksi.

**Gerbang selesai tahap 9:** setiap komentar valid memperoleh satu prediksi, penanganan kesalahan jelas, dan batch tidak mencampur hasil dataset lain.

### Tahap 10 — Pengujian integrasi dan keamanan

Jalankan dan dokumentasikan pengujian minimal berikut:
- Register, login, logout, dan session.
- Akses halaman privat tanpa login.
- User biasa mencoba route Superadmin melalui URL/API langsung.
- Upload CSV valid, tidak valid, kosong, salah kolom, dan encoding bermasalah.
- Label manual tidak ditimpa lexicon.
- Skor lexicon tidak meyakinkan masuk status review sesuai aturan.
- Metadata sumber label tidak terkirim ke user biasa.
- Preprocessing termasuk pengujian negasi.
- Training/evaluasi tiga kelas dan confusion matrix 3 × 3.
- Pemuatan ulang pasangan model/vectorizer.
- Single testing sebelum dan sesudah model tersedia.
- Batch testing dengan sebagian baris invalid.
- Isolasi dataset/resource antar pengguna.
- Tampilan loading, success, empty, dan error state.

**Gerbang selesai tahap 10:** seluruh hasil pengujian dicatat dengan status Passed/Failed/Not Run. Jangan menyebut test Passed jika test belum dijalankan.

### Tahap 11 — Finalisasi dan dokumentasi

1. Periksa konsistensi UI dengan prototype dan aturan dalam `STRICT.md`.
2. Periksa agar seluruh UI, contoh teks, README, label, dan data demo hanya menyebut aktivitas pertambangan PT Freeport Indonesia.
3. Pastikan tidak ada password, token, connection string, file model privat, atau dataset sensitif yang ikut ter-commit.
4. Lengkapi `README.md`, `.env.example`, dependency, instruksi MySQL, migration/schema, dan perintah test.
5. Buat laporan penyelesaian berisi: fitur selesai, file utama yang berubah, setup/running steps, test yang dijalankan beserta hasil, dan gap yang belum selesai.
6. Sebut fitur sebagai “selesai” hanya jika diimplementasikan dan diverifikasi. Fitur yang masih mockup/placeholder harus dinyatakan demikian.

---

## 4. Aturan Komunikasi dan Pelaksanaan Agent

- Kerjakan secara bertahap dan hindari perubahan besar yang tidak dapat ditinjau.
- Sebelum tahap yang mengubah banyak file, sampaikan rencana singkat dan daftar file terdampak.
- Setelah setiap tahap, jalankan pengujian relevan dan rangkum hasil aktual.
- Jika ada detail yang tidak ditentukan oleh PRD/BSD/TSD, pilih implementasi sederhana yang konsisten, dokumentasikan asumsi, dan jangan mengarang kebutuhan bisnis baru.
- Jangan berhenti setelah membuat UI statis jika tugas meminta fitur berjalan; sambungkan UI, route, service, dan database.
- Jangan mengganti stack Flask/HTML/CSS/JavaScript/MySQL tanpa persetujuan pemilik proyek.

## 5. Definisi Selesai Proyek

Proyek dinyatakan selesai hanya ketika:
1. Semua halaman utama sesuai prototype.
2. Login/role dan pembatasan Superadmin berfungsi di backend.
3. CSV tervalidasi dan tersimpan secara konsisten.
4. Lexicon mendahului preprocessing dan tidak menimpa label manual.
5. Preprocessing, TF-IDF, training SVM, evaluasi 3 kelas, single testing, dan batch testing dapat dijalankan.
6. MySQL menyimpan informasi yang dibutuhkan dan artefak model/vectorizer terhubung ke eksperimen yang benar.
7. Hasil metrik berasal dari eksperimen nyata.
8. Pengujian dan keterbatasan didokumentasikan.
