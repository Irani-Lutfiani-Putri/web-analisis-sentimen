# STRICT.md — Aturan Wajib / Non-Negotiable

Dokumen ini berisi batasan keras yang wajib dipatuhi AI coding agent saat bekerja pada aplikasi. Jika instruksi implementasi lain bertentangan dengan dokumen ini, **ikuti STRICT.md** dan minta persetujuan pemilik proyek sebelum menyimpang.

## A. Batasan Studi Kasus

1. **Satu-satunya studi kasus aktif adalah aktivitas pertambangan PT Freeport Indonesia.**
2. Jangan menampilkan, mengaktifkan, atau menambahkan studi kasus, isu, perusahaan, komoditas, atau dataset di luar fokus tersebut ke dalam aplikasi, UI, data demo, maupun dokumentasi produk.
3. Gunakan judul penelitian secara konsisten: **“Analisis Sentimen Komentar YouTube terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Algoritma Support Vector Machine.”**
4. Jangan mengubah fokus menjadi sentimen terhadap perusahaan secara umum jika komentar dan definisi dataset secara khusus berkaitan dengan aktivitas pertambangan.
5. Jangan mengarang sumber data, jumlah komentar, tanggal pengambilan data, label, skor lexicon, hasil prediksi, akurasi, precision, recall, F1-score, atau status implementasi.

## B. Aturan UI/UX — Ikuti PRD dan Prototype

1. Pertahankan desain minimalis monokromatik hitam, putih, dan abu-abu/slate.
2. Pertahankan hirarki visual, sidebar, kartu, tabel, ukuran judul, tombol, jarak, radius, dan gaya form prototype sejauh aset tersedia.
3. Utamakan desktop web sekitar 1280–1440 px, namun jangan membuat antarmuka rusak pada layar lebih kecil.
4. Halaman utama yang diizinkan: Landing Page, Login, Register, Import Dataset, Dashboard, Preprocessing, Klasifikasi, dan Testing.
5. Sidebar halaman kerja harus tetap mengikuti prototype: **Dashboard, Preprocessing, Klasifikasi, Testing, Logout**. Kelola Akun hanya jika fitur tersebut memang ada pada rancangan/ruang lingkup implementasi.
6. **Jangan menambahkan menu utama “Lexicon” ke sidebar.** Lexicon adalah langkah pertama di dalam halaman Preprocessing.
7. Hasil dan evaluasi tampil pada halaman Klasifikasi bila mengikuti prototype; jangan membuat menu utama Evaluasi baru.
8. Jangan merombak UI menjadi desain baru, menambah wizard besar, atau membuat halaman tambahan tanpa persetujuan pemilik proyek.
9. Setiap nilai ringkasan harus dari database atau proses aktual. Bila belum ada data, tampilkan empty state yang jelas.
10. Data contoh harus diberi label “Contoh/Demo” secara terlihat dan tidak boleh bercampur dengan data penelitian.

## C. Urutan Proses yang Wajib

Urutan default sistem:

**Upload Dataset → Pelabelan Lexicon → Preprocessing → Klasifikasi SVM → Hasil dan Evaluasi → Testing.**

1. Tahap Lexicon harus tampil sebagai langkah pertama dalam halaman Preprocessing, bukan menu utama tersendiri.
2. Lexicon boleh melakukan normalisasi ringan internal untuk pencocokan, tetapi preprocessing penelitian tetap dilakukan setelah tahap tersebut.
3. Label manual yang sudah sah harus diprioritaskan dan tidak boleh ditimpa lexicon.
4. Lexicon hanya menetapkan label otomatis pada komentar yang belum memiliki label manual.
5. Komentar ambigu, skor nol, polaritas campuran, negasi, sarkasme, dan hasil lexicon yang tidak meyakinkan tidak boleh secara otomatis dipaksa menjadi Netral. Tandai untuk review sesuai aturan yang terdokumentasi.
6. Label training wajib valid: `Positif`, `Negatif`, atau `Netral`.
7. Training, evaluasi, dan testing hanya dapat berjalan jika prasyaratnya terpenuhi. Jika belum, tampilkan pesan yang menerangkan langkah yang harus dilakukan.

## D. Hak Akses dan Privasi Pelabelan

1. Hanya role `superadmin` yang boleh melakukan pelabelan manual atau mengubah label manual.
2. Hanya Superadmin yang boleh melihat `label_source`, `lexicon_score`, identitas pelabel, waktu pelabelan, catatan anotasi, serta riwayat internal pelabelan.
3. Pengguna biasa boleh melihat komentar dan label sentimen akhir jika diizinkan, tetapi tidak boleh menerima metadata internal pelabelan melalui HTML, JSON/API, atribut data, atau response tersembunyi.
4. Otorisasi harus diperiksa di backend pada setiap route/endpoint; jangan mengandalkan penyembunyian tombol, CSS, JavaScript, atau pemeriksaan frontend.
5. Uji akses dengan memanggil endpoint langsung sebagai user biasa, bukan hanya memastikan tombol tidak terlihat.
6. Registrasi publik tidak boleh menerima role Superadmin dari request. Akun baru harus menjadi `user`.
7. Password tidak boleh disimpan dalam bentuk plaintext.
8. Catat akun dan waktu untuk perubahan label manual. Jangan mengubah sumber label atau riwayat secara diam-diam.

## E. Aturan Lexicon dan Label

1. Simpan kolom label manual dan label lexicon secara terpisah; jangan menyatukan asal label sampai tidak bisa ditelusuri.
2. Simpan sumber label, skor, status review, dan informasi audit di database.
3. Label akhir ditentukan dengan aturan eksplisit: label manual valid diprioritaskan; jika tidak ada, gunakan label lexicon yang memenuhi aturan; jika hasil meragukan, tandai perlu review.
4. Jangan mengklaim hasil lexicon sebagai kebenaran anotator atau sebagai ground truth independen.
5. Jangan menggunakan test set berlabel manual untuk training atau penyetelan model.
6. Untuk evaluasi SVM yang dapat dipertanggungjawabkan, gunakan data uji manual yang terpisah dari training; dokumentasikan bila jumlah data manual belum mencukupi.
7. Tangani negasi Bahasa Indonesia seperti “tidak”, “bukan”, dan “belum”; jangan membuangnya secara membabi buta pada stopword removal.
8. Setiap perubahan kamus lexicon atau ambang label harus terdokumentasi dan konsisten dengan eksperimen yang menyimpan hasilnya.

## F. Aturan Machine Learning dan Integritas Evaluasi

1. Gunakan TF-IDF dan Support Vector Machine (SVM) sesuai ruang lingkup.
2. Lakukan split train/test sebelum fitting TF-IDF.
3. Fit `TfidfVectorizer` hanya pada teks training. Transform test/inference menggunakan vectorizer yang sama.
4. Dilarang fit vectorizer pada seluruh dataset sebelum split karena menimbulkan data leakage.
5. Pastikan model dan vectorizer dari eksperimen yang sama selalu dipasangkan.
6. Evaluasi tiga kelas wajib memakai confusion matrix **3 × 3**, dengan label kelas dan sumbu aktual/prediksi yang jelas.
7. Tampilkan accuracy, precision, recall, F1-score, metrik per kelas, serta nyatakan agregat macro/weighted yang digunakan.
8. Jangan menampilkan probabilitas/confidence kecuali model secara eksplisit menghasilkan nilai tersebut dengan konfigurasi yang benar.
9. Jangan mengisi metrik dengan angka dummy, menyalin hasil contoh sebagai hasil penelitian, atau menyatakan model sudah terlatih sebelum benar-benar dilatih dan diverifikasi.
10. Jika training/evaluasi gagal, tampilkan error dan status gagal. Jangan menampilkan status sukses palsu.

## G. Teknologi dan Struktur Teknis

1. Stack yang harus dipertahankan: **Flask + HTML + CSS + JavaScript + MySQL + pandas + scikit-learn + Sastrawi**.
2. Jangan mengganti MySQL dengan SQLite, JSON lokal, atau database lain kecuali pemilik proyek secara eksplisit menyetujui perubahan.
3. Pisahkan route/controller, service/business logic, model database, template, CSS, dan JavaScript sesuai struktur repositori.
4. Jangan mengerjakan seluruh logika aplikasi hanya dalam satu file jika struktur modular telah ditetapkan.
5. Kredensial dan `SECRET_KEY` berasal dari environment variables. Jangan menaruh rahasia asli di source code atau repository.
6. Gunakan ORM atau parameterized queries; hindari SQL injection.
7. Terapkan validasi server-side walaupun validasi frontend tersedia.
8. File upload dan model/vectorizer harus disimpan di lokasi privat di luar folder static yang dapat diakses publik.
9. Validasi format, ukuran, encoding, kolom, dan isi CSV di server.
10. Jangan menampilkan traceback, kredensial, connection string, atau path internal kepada pengguna.

## H. Aturan Perubahan Kode

1. Audit kode yang sudah ada sebelum membuat/menghapus file.
2. Jangan menghapus fungsi yang telah bekerja tanpa alasan teknis dan penjelasan.
3. Jangan membuat data mock terlihat seperti data nyata.
4. Jangan meninggalkan tombol yang tampak berfungsi tetapi tidak menjalankan aksi. Jika fitur belum diimplementasikan, tandai secara jelas.
5. Jangan menyatakan suatu fitur “selesai” kecuali implementasi dan pengujian terkait sudah dilakukan.
6. Setelah perubahan, jalankan tes yang relevan dan laporkan hasil sebenarnya: Passed, Failed, atau Not Run.
7. Jangan menciptakan route, tabel, file konfigurasi, atau dependensi baru yang tidak diperlukan tanpa memeriksa struktur proyek lebih dahulu.
8. Perubahan besar harus dilakukan per tahap agar mudah ditinjau dan dibatalkan bila perlu.

## I. Syarat Kelulusan Wajib

Pekerjaan tidak boleh dinyatakan selesai jika salah satu hal berikut belum terpenuhi atau belum dijelaskan sebagai keterbatasan:

- [ ] Topik, seluruh halaman, teks UI, dan dokumentasi hanya membahas aktivitas pertambangan PT Freeport Indonesia.
- [ ] UI sesuai prototype/PRD awal dan tidak memiliki menu utama Lexicon tersendiri.
- [ ] Urutan Lexicon → Preprocessing → SVM sesuai ketentuan.
- [ ] Label manual tidak tertimpa lexicon.
- [ ] Metadata sumber label dan pelabelan manual terlindungi di backend untuk Superadmin.
- [ ] Data CSV divalidasi dan disimpan secara benar di MySQL.
- [ ] TF-IDF bebas data leakage dan artefak cocok dengan model.
- [ ] Evaluasi tiga kelas memakai confusion matrix 3 × 3 dan metrik aktual.
- [ ] Single testing dan batch testing diuji.
- [ ] Tidak ada angka hasil, jumlah data, atau status model yang dikarang.
- [ ] Konfigurasi setup dan hasil tes didokumentasikan.
