# STRICT.md — Aturan Wajib / Non-Negotiable

Dokumen ini berisi batasan keras yang wajib dipatuhi AI coding agent saat bekerja pada aplikasi. Jika instruksi implementasi lain bertentangan dengan dokumen ini, **ikuti STRICT.md** dan minta persetujuan pemilik proyek sebelum menyimpang.

## A. Batasan Studi Kasus

1. **Satu-satunya studi kasus aktif adalah aktivitas pertambangan PT Freeport Indonesia.**
2. Jangan menampilkan, mengaktifkan, atau menambahkan studi kasus, isu, perusahaan, komoditas, atau dataset di luar fokus tersebut ke dalam aplikasi, UI, data demo, maupun dokumentasi produk.
3. Gunakan judul penelitian secara konsisten: **“Analisis Sentimen Komentar YouTube terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Algoritma Support Vector Machine.”**
4. Jangan mengubah fokus menjadi sentimen terhadap perusahaan secara umum jika komentar dan definisi dataset secara khusus berkaitan dengan aktivitas pertambangan.
5. Jangan mengarang sumber data, jumlah komentar, tanggal pengambilan data, label, skor lexicon, hasil prediksi, akurasi, precision, recall, F1-score, atau status implementasi.

## B. Aturan UI/UX — Ikuti Keputusan Desain Terbaru

Keputusan pemilik proyek tanggal 27 Oktober 2026 ini menggantikan aturan visual/navigasi lama yang bertentangan. Referensi utama adalah `stitch_unified_ui_design_system.zip`, tetapi seluruh domain, teks, data, dan metode wajib disesuaikan untuk studi kasus aktivitas pertambangan PT Freeport Indonesia.

1. Gunakan design system modern SaaS dengan magenta/pink pastel, kartu putih, latar lembut, radius konsisten, spacing lega, dan komponen responsif.
2. Gunakan token warna: primary `#F13E93`, primary-soft `#F891BB`, accent `#F9D0CD`, info/highlight `#FAFFCB`, page `#FFF7F9`, surface `#FFFFFF`, text `#23121B`, muted `#7A6671`.
3. Warna semantik sentimen: Positif `#10B981` dengan latar `#E6F4EA`; Netral `#F59E0B` dengan latar `#FEF3C7`; Negatif `#EF4444` dengan latar `#FEE2E2`. Jangan menggunakan magenta untuk menyamarkan kategori sentimen.
4. Utamakan desktop sekitar 1280–1440 px tetapi wajib responsif. Uji paling sedikit 390 px, 768 px, 1024 px, dan 1366/1440 px. Sidebar desktop berada di kiri; tablet dapat dilipat; mobile menggunakan drawer.
5. Halaman produk yang diizinkan: Landing Page, Login, Register, Dashboard, Preprocessing, Klasifikasi, Hasil Klasifikasi, Testing, serta Kelola Dataset khusus Superadmin.
6. Sidebar halaman kerja: **Dashboard, Preprocessing, Klasifikasi, Hasil Klasifikasi, Testing, Logout**. Menu **Kelola Dataset** hanya untuk Superadmin.
7. Impor dataset dimulai melalui modal **Impor Dataset** dari Dashboard, bukan menu sidebar permanen. Route upload yang sudah ada boleh dipertahankan sebagai fallback/deep link dan handler backend.
8. Setelah login berhasil, arahkan pengguna ke Dashboard. Jika pengguna belum memiliki dataset, buka modal Impor Dataset secara otomatis. Jangan membuka modal berulang pada setiap refresh; batasi prompt otomatis per login/session. Pengguna yang sudah memiliki dataset masuk ke Dashboard normal.
9. Dashboard harus menyediakan tombol untuk membuka kembali modal Impor Dataset. Modal berisi upload CSV dan field kolom yang memang didukung backend; jangan menambahkan preset/dataset wisata Bali atau dukungan format yang belum ada.
10. Jika upload gagal, tampilkan error yang aman dan dapat dipahami di modal sehingga pengguna dapat memilih ulang berkas. Jika upload berhasil, ikuti proses backend yang ada: simpan ke MySQL, jalankan pelabelan InSet otomatis bila kamus valid tersedia, lalu arahkan ke Preprocessing dan tampilkan status job aktual.
11. **Jangan menambahkan menu utama “Lexicon”.** Lexicon adalah langkah pertama pada halaman Preprocessing.
12. Training dan pengaturan model berada di halaman Klasifikasi; ringkasan eksperimen, metrik, confusion matrix, dan hasil evaluasi tampil pada halaman terpisah **Hasil Klasifikasi**. Jangan membuat menu Evaluasi ketiga.
13. Setiap nilai ringkasan, grafik, jumlah data, progres, label, dan metrik harus berasal dari database atau proses aktual. Jika data belum tersedia, tampilkan empty state. Jangan memakai angka contoh dari referensi sebagai hasil penelitian.
14. Gunakan modal yang aksesibel: judul terhubung ke dialog, fokus keyboard dikelola, tersedia tombol tutup dan dukungan Escape, error diumumkan dengan benar, dan interaksi keyboard tidak rusak.
15. Jangan membuat wizard yang mengunci navigasi. Pengguna tetap dapat membuka halaman lain, tetapi sistem harus menjelaskan jika prasyarat pada halaman tersebut belum terpenuhi.
16. Pertahankan aturan role, CSRF, dan otorisasi backend. Penyembunyian tombol/menu di frontend bukan pengganti pemeriksaan server.
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

- [ ] Topik, seluruh halaman, teks UI, dan dokumentasi produk hanya membahas aktivitas pertambangan PT Freeport Indonesia.
- [ ] Design system magenta/pink pastel diterapkan konsisten dan responsif; bukan lagi memakai aturan monokrom lama.
- [ ] Login pengguna tanpa dataset menampilkan modal Impor Dataset di atas Dashboard; pengguna yang punya dataset tidak dipaksa melihat modal setiap refresh.
- [ ] Modal impor dapat dibuka kembali dari Dashboard, mengirim CSV ke backend yang ada, mempertahankan CSRF/validasi, serta menampilkan pesan error dan sukses yang benar.
- [ ] Sidebar memuat Dashboard, Preprocessing, Klasifikasi, Hasil Klasifikasi, Testing, dan Logout; Kelola Dataset hanya untuk Superadmin.
- [ ] Tidak ada menu utama Lexicon. Lexicon → Preprocessing tetap sesuai urutan wajib.
- [ ] Klasifikasi terpisah dari Hasil Klasifikasi; hasil hanya memakai eksperimen completed dan data aktual.
- [ ] Progress, metrik, jumlah data, dan status proses bukan animasi/angka palsu.
- [ ] Label manual tidak tertimpa lexicon.
- [ ] Metadata sumber label dan pelabelan manual terlindungi di backend untuk Superadmin.
- [ ] Data CSV divalidasi dan disimpan dengan benar di MySQL.
- [ ] TF-IDF bebas data leakage dan artefak vectorizer selalu cocok dengan model.
- [ ] Evaluasi tiga kelas memakai confusion matrix 3 × 3 dan metrik aktual.
- [ ] Single testing dan batch testing diuji.
- [ ] Tidak ada angka hasil, jumlah data, atau status model yang dikarang.
- [ ] Tes backend, keamanan, dan responsive UI dijalankan atau keterbatasan yang belum diuji dilaporkan dengan jelas.
- [ ] Konfigurasi setup dan hasil tes didokumentasikan.
