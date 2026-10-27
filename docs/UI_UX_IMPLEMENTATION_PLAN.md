# Agent Handoff — Implementasi UI/UX Web Analisis Sentimen Freeport

**Repository:** `Irani-Lutfiani-Putri/web-analisis-sentimen`  
**Stack wajib:** Flask, Jinja/HTML, CSS, JavaScript, MySQL, pandas, scikit-learn, Sastrawi.  
**Status:** Rencana implementasi per phase. Jangan mengubah business logic atau data penelitian hanya demi desain.

## 0. Instruksi utama

Sebelum coding, baca `STRICT.md`, `README.md`, route, model database, services, templates, CSS/JS, migration, dan tests yang relevan. Audit perilaku yang sudah bekerja dan lakukan perubahan sekecil mungkin. Kerjakan satu phase pada satu waktu; setelah setiap phase, jalankan tes relevan dan laporkan hasil sebenarnya. Jangan mengklaim fitur/tes berhasil jika belum dijalankan.

Referensi `stitch_unified_ui_design_system.zip` hanya acuan visual dan interaksi. Jangan menyalin isi wisata Bali, dataset preset, Random Forest, angka contoh, atau metrik dari referensi.

## 1. Keputusan produk yang disetujui

- Topik: **Analisis Sentimen Komentar YouTube terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Algoritma Support Vector Machine.**
- Kelas: Positif, Netral, Negatif. Metode: TF-IDF + SVM.
- Stack dan database MySQL tetap. Jangan mengganti framework, database, algoritma, atau membuat aplikasi baru.
- Lexicon InSet adalah label otomatis awal, bukan ground truth evaluasi.
- Evaluasi wajib menggunakan holdout manual independen yang tidak digunakan untuk training/tuning. TF-IDF di-fit hanya pada data training setelah split; test hanya ditransform dengan vectorizer yang sama.
- Role/CSRF/otorisasi backend dan perlindungan metadata label tetap wajib.

### Design tokens

| Peran | Nilai |
|---|---|
| Primary | `#F13E93` |
| Primary soft | `#F891BB` |
| Accent | `#F9D0CD` |
| Info/highlight | `#FAFFCB` |
| Page background | `#FFF7F9` |
| Surface/card | `#FFFFFF` |
| Text | `#23121B` |
| Muted text | `#7A6671` |
| Positif / latar | `#10B981` / `#E6F4EA` |
| Netral / latar | `#F59E0B` / `#FEF3C7` |
| Negatif / latar | `#EF4444` / `#FEE2E2` |

Buat token CSS di satu tempat. Gunakan kartu putih, radius/spacing konsisten, sidebar kiri, navbar atas, tombol dan badge yang seragam. Pastikan kontras, focus-visible, label form, keyboard navigation, dan responsivitas. Jangan menambah framework/build step baru tanpa alasan setelah audit.

### Navigasi

Sidebar: Dashboard, Preprocessing, Klasifikasi, Hasil Klasifikasi, Testing, Logout. Kelola Dataset hanya untuk Superadmin. Jangan buat menu utama Lexicon atau Evaluasi terpisah. Impor Dataset dimulai dari modal di Dashboard; route upload lama boleh dipertahankan sebagai handler/fallback.

### Perilaku setelah login

- Login berhasil → Dashboard.
- Jika pengguna belum memiliki dataset, modal Impor Dataset otomatis terbuka di atas Dashboard.
- Jika sudah memiliki dataset, Dashboard terbuka normal; tombol Impor Dataset tetap dapat membuka modal kapan saja.
- Jangan memunculkan modal terus-menerus setiap refresh. Gunakan flag session/per-login atau mekanisme setara yang terdokumentasi.
- Tutup modal tidak menghapus data. Modal harus aksesibel (judul dialog, fokus keyboard, tombol tutup, Escape, pesan error yang jelas).
- Upload gagal → tampilkan error aman di modal dan izinkan pilih berkas ulang.
- Upload berhasil → validasi dan simpan ke MySQL menggunakan backend yang ada, mulai pelabelan InSet otomatis sesuai mekanisme saat ini, lalu arahkan ke Preprocessing dengan status job aktual.
- Jangan menambah preset wisata Bali, dataset demo, atau dukungan XLSX bila backend tidak mendukungnya.

## 2. Workflow yang harus tetap benar

`Login → Dashboard/modal impor → validasi CSV → MySQL → pelabelan InSet otomatis → Preprocessing/review → Klasifikasi SVM → Hasil Klasifikasi/evaluasi → Testing single/batch`.

Ini bukan wizard yang mengunci sidebar. Pengguna dapat membuka halaman kapan saja; halaman menjelaskan status dan prasyarat aktual. Tombol tidak boleh tampak berfungsi bila belum diimplementasikan.

## 3. Implementasi per phase

### Phase 0 — Audit dan dokumentasi

- Baca `STRICT.md`, `README.md`, semua route, models, services, templates, CSS/JS, migration, dan tes terkait.
- Petakan fungsi/route yang sudah berjalan dan perubahan minimal yang diperlukan.
- Perbarui dokumentasi UI/UX yang bertentangan, terutama `STRICT.md`, tanpa mengubah aturan studi kasus, keamanan, lexicon, atau validitas ML.
- Jangan ubah kode aplikasi pada phase ini.

**Selesai jika:** tidak ada aturan visual/navigasi yang saling bertentangan; fitur existing yang harus dipertahankan sudah dipetakan.

### Phase 1 — Design system dan layout global

Kemungkinan file: `app/static/css/style.css`, `app/templates/base.html`, aset statis terkait.

- Terapkan tokens warna, typography, button states, cards, form controls, tables, alerts, badges, loading/empty/error states.
- Redesain sidebar/navbar; menu aktif mengikuti halaman aktual. Kelola Dataset hanya Superadmin.
- Desktop sidebar tetap; tablet dapat dilipat; mobile menjadi drawer yang bisa dibuka/tutup dan ramah keyboard.
- Tabel lebar boleh scroll horizontal; jangan sampai seluruh halaman overflow.
- Pertahankan handler logout/CSRF dan seluruh link yang berfungsi.

**Selesai jika:** semua halaman memakai layout konsisten, link bekerja, focus terlihat, tidak ada overflow global pada 390 px.

### Phase 2 — Dashboard dan modal Impor Dataset

Kemungkinan file: `app/routes/auth.py`, `app/templates/dashboard/index.html`, `app/templates/datasets/upload.html`, `base.html`, JS modal, tes.

- Dashboard memakai data aktual dari MySQL: jumlah komentar, distribusi sentimen, dataset aktif/terbaru. Jika belum ada data, gunakan empty state; jangan buat angka dummy.
- Tambahkan tombol Impor Dataset yang membuka modal.
- Modal menerima CSV dan hanya kolom yang didukung backend. Label manual opsional hanya jika alur tersebut sudah didukung dan sesuai role.
- Hubungkan modal ke handler upload yang ada. Pertahankan CSRF, validasi format/ukuran/encoding/kolom, nama file aman, penyimpanan privat.
- Error upload harus bisa ditampilkan di modal setelah redirect, tanpa traceback/path internal. Pengguna harus bisa memilih berkas ulang.
- Prompt otomatis hanya pada kondisi pengguna belum memiliki dataset dan tidak boleh terus muncul pada setiap refresh.
- Sukses mengikuti alur backend aktual; jangan menampilkan status selesai palsu.

**Selesai jika:** user baru melihat modal di Dashboard; user yang punya dataset masuk Dashboard normal; CTA membuka modal; CSV invalid memberi error; CSV valid tersimpan dan mengikuti flow preprocessing.

### Phase 3 — Preprocessing dan Kelola Dataset

Kemungkinan file: `app/templates/preprocessing/index.html`, `app/templates/admin_datasets/index.html`, route/service dan tes terkait.

- Susun UI menjadi status/pelabelan InSet, preprocessing teks, preview perbandingan, dan aksi lanjut ke Klasifikasi.
- InSet tetap otomatis setelah impor bila kamus tersedia. Jangan memaksa user mengulangi proses otomatis.
- Progres harus mencerminkan status job backend, bukan persentase animasi palsu.
- Tampilkan teks asli dan hasil hanya jika tersedia. Tambahkan empty/loading/error state.
- Fitur review/koreksi label/holdout hanya untuk Superadmin. Metadata internal label tidak boleh dikirim ke user biasa melalui HTML/API/atribut data.
- Label manual sah tidak boleh ditimpa InSet.

**Selesai jika:** progres dan teks sesuai data aktual; akses Superadmin diuji dengan request langsung; label manual tetap terlindungi.

### Phase 4 — Pisahkan Klasifikasi dan Hasil Klasifikasi

Kemungkinan file: route klasifikasi, `app/templates/classification/index.html`, template hasil baru, nav, tests.

- Klasifikasi fokus pada dataset, checklist kesiapan, konfigurasi aktual, dan tombol training.
- Tambahkan halaman Hasil Klasifikasi terpisah (misalnya route `/classification/results`) setelah mengaudit struktur route yang ada.
- Gunakan eksperimen/model run yang sudah disimpan. Jangan membuat tabel baru kecuali audit menunjukkan benar-benar perlu.
- Hasil hanya untuk run completed yang boleh diakses pengguna tersebut.
- Tampilkan accuracy, precision, recall, F1-score macro/weighted, metrik per kelas, confusion matrix 3×3, jumlah train/test dan metadata eksperimen yang benar-benar tersedia.
- Jangan salin angka contoh dari ZIP (mis. 85.37%, 80:20, jumlah baris) menjadi hasil aktual.
- Holdout harus manual independen. Split sebelum fit TF-IDF; fit vectorizer hanya pada training. Model dan vectorizer harus berasal dari eksperimen sama.
- Training gagal harus menunjukkan error; jangan tampilkan hasil sukses.

**Selesai jika:** halaman training dan hasil terpisah; metrik berasal dari run aktual; tidak ada data leakage; tes akses run milik user lain ditolak.

### Phase 5 — Testing

Kemungkinan file: `app/templates/testing/index.html`, route/service hanya jika perlu, CSS/JS dan tes.

- Buat panel/tab single comment dan batch CSV.
- Single: masukkan komentar, submit, status, hasil label aktual.
- Batch: validasi CSV, tampilkan baris valid/ditolak, jumlah prediksi per kelas dan tabel hasil.
- Gunakan model dan vectorizer yang cocok dari eksperimen completed. Jangan tampilkan confidence/probability jika model tidak menghasilkan nilai tersebut.
- Error aman dan informatif; tidak ada traceback/path internal.

**Selesai jika:** single dan batch bekerja, hasil berasal dari model aktual, tabel tetap usable di mobile.

### Phase 6 — QA, keamanan, aksesibilitas, regresi

- Jalankan tes project menggunakan database test terpisah (`TEST_DATABASE_URL`), jangan menjalankan tes destruktif terhadap database penelitian.
- Ikuti perintah tes di README; pada Windows/Laragon gunakan perintah yang terdokumentasi (contoh `.venv/Scripts/python.exe -m pytest tests -q`). Laporkan Passed/Failed/Not Run secara jujur.
- Audit breakpoint 390, 768, 1024, 1366/1440 px.
- Uji keyboard: fokus terlihat, modal membuka/menutup dengan benar, Escape berfungsi, drawer dapat dikendalikan, label input terhubung.
- Uji endpoint langsung sebagai user biasa untuk aksi Superadmin; pastikan CSRF/otorisasi backend tidak berubah.
- Cari string wisata Bali, Random Forest, angka dummy, dan data demo yang terbawa.
- Review diff agar tidak ada perubahan algoritma/schema/dependency yang tidak diperlukan.

**Selesai jika:** tes dan keterbatasan dilaporkan, tidak ada regresi upload/lexicon/preprocessing/SVM/evaluasi/testing, dan UI responsif.

## 4. Pemetaan awal kode (verifikasi melalui audit)

- Layout: `app/templates/base.html`
- Dashboard: `app/routes/auth.py`, `app/templates/dashboard/index.html`
- Upload: `app/routes/datasets.py`, `app/templates/datasets/upload.html`
- Preprocessing/lexicon: `app/routes/preprocessing.py`, `app/routes/admin_datasets.py`, services, template preprocessing/admin
- Training: `app/routes/classification.py`, `app/services/training_service.py`
- Testing: `app/routes/testing.py`, `app/services/prediction_service.py`
- CSS/progress: `app/static/css/style.css`, `app/static/js/progress-dialog.js`
- Hasil saat ini mungkin masih berada di template klasifikasi; verifikasi sebelum memindahkan.

Daftar ini tidak menggantikan pembacaan file dan tes lengkap.

## 5. Larangan

- Jangan mengganti MySQL, Flask, SVM, TF-IDF, atau Sastrawi.
- Jangan mengarang data, label, tanggal, jumlah komentar, hasil, metrik, atau progres.
- Jangan menganggap InSet sebagai ground truth independen.
- Jangan fit TF-IDF sebelum split.
- Jangan membocorkan metadata pelabelan ke user biasa.
- Jangan mengandalkan frontend untuk otorisasi.
- Jangan menghapus fungsi existing tanpa alasan teknis.
- Jangan menambahkan progress bar persentase bila backend tidak menyediakan progres aktual.
- Jangan mengklaim tes/phase lulus tanpa menjalankannya.

## 6. Laporan wajib setiap phase

Setiap phase harus melaporkan:
1. Ringkasan perubahan.
2. File yang dibuat/diubah.
3. Perilaku yang diuji.
4. Perintah tes dan hasil: Passed / Failed / Not Run.
5. Risiko atau pekerjaan tersisa.
6. Konfirmasi bahwa domain Freeport, role/CSRF, MySQL, dan validitas evaluasi tidak berubah.

Lanjut ke phase berikutnya hanya setelah phase aktif lulus atau keterbatasannya dilaporkan dengan jelas.
