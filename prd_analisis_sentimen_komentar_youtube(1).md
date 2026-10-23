# Product Requirements Document (PRD) & Project Brief

**Project Name:** Sistem Analisis Sentimen Komentar YouTube Berbasis Support Vector Machine (SVM)  
**Context / Case Study:** Analisis Sentimen Komentar YouTube terhadap Isu Kenaikan Harga BBM & Aktivitas Pertambangan PT Freeport Indonesia  
**Document Version:** 1.0  
**Status:** Approved / In Implementation  
**Target Platform:** Web Desktop Application  

---

## 1. Executive Summary & Project Brief

### 1.1 Background & Purpose
Opini publik di platform media sosial seperti YouTube sering kali mencerminkan sentimen masyarakat terhadap isu-isu krusial nasional, termasuk dinamika kenaikan harga BBM dan operasi pertambangan PT Freeport Indonesia. Untuk memahami polaritas opini tersebut secara objektif dan terukur, diperlukan sistem berbasis Natural Language Processing (NLP) dan algoritma Machine Learning Support Vector Machine (SVM) yang dapat mengotomatisasi pengumpulan, pembersihan data, pelatihan model, serta pengujian inferensi data baru.

### 1.2 Core Objectives
1. **Automated Pipeline:** Mengintegrasikan seluruh siklus NLP mulai dari upload dataset CSV, preprocessing teks, representasi bobot fitur (TF-IDF), hingga pelatihan model SVM.
2. **Visual Analytics:** Memberikan visualisasi ringkas dan akurat terkait persepsi publik (Positif, Netral, Negatif).
3. **Interactive Testing:** Menyediakan fasilitas pengujian real-time untuk kalimat baru (*single inference*) dan uji coba batch menggunakan file CSV terpisah.

---

## 2. Target Users & Personas

1. **Peneliti / Mahasiswa / Data Scientist:** Pengguna teknis yang memerlukan transparansi pipeline (tahap preprocessing, pembagian split data, dan evaluasi matriks performa model).
2. **Analis Kebijakan / PR / Stakeholder:** Pengguna manajerial yang berfokus pada hasil analisis sentimen di dashboard untuk pengambilan keputusan atau penyusunan laporan respons publik.
3. **Admin Sistem:** Pengguna yang mengelola otentikasi (login/register) dan upload dataset utama.

---

## 3. Product Architecture & User Flow

```
[Landing Page] 
       │
       ├──► [Login] / [Register]
       │
       ▼
[Dashboard Analisis Sentimen]
       │
       ├──► [Upload Dataset] (.csv import)
       │
       ├──► [Tahap Preprocessing]
       │       (Cleaning, Lowercase, Stopwords, Stemming)
       │
       ├──► [Klasifikasi SVM]
       │       (TF-IDF ➔ Split Data ➔ Training SVM ➔ Evaluasi)
       │
       └──► [Testing Model]
               ├── Single Input (Cek Kalimat Baru)
               └── Batch CSV Testing (Cek Data Testing)
```

---

## 4. Detailed Feature Specifications & Screen Breakdown

### Screen 1: Landing Page (`{{DATA:SCREEN:SCREEN_15}}`)
* **Role:** Halaman publik pengantar dan gerbang akses utama.
* **Key Components:**
  * Top Navigation Bar: Brand title "ANALISIS SENTIMEN KOMENTAR YOUTUBE", Menu link (*Tentang*, *Pertambangan*, *Dashboard*).
  * Hero Section: Tipografi display berukuran besar "ANALISIS SENTIMEN" bergaya bold/outline.
  * Deskripsi Studi Kasus: "Analisis Sentimen Komentar YouTube Terhadap Aktivitas Pertambangan PT Freeport Indonesia Menggunakan Algoritma Support Vector Machine".
  * Primary CTA Button: "Mulai Analisis" mengarahkan pengguna ke alur otentikasi/dashboard.

### Screen 2 & 3: Otentikasi - Login & Register (`{{DATA:SCREEN:SCREEN_13}}`, `{{DATA:SCREEN:SCREEN_11}}`)
* **Role:** Gerbang keamanan dan identifikasi pengguna.
* **Key Components:**
  * **Login Screen:** Input Email, Password, Tombol CTA "Masuk", navigasi header ringkas.
  * **Register Screen:** Input Nama Lengkap, Email, Password, Tombol CTA "Daftar".
  * Styling: Desain minimalis monokromatik dengan container terpusat (*center card*).

### Screen 4: Import Dataset (`{{DATA:SCREEN:SCREEN_9}}`)
* **Role:** Modul input data primer untuk analisis.
* **Key Components:**
  * Header & Instruksi: "Unggah dataset komentar YouTube dalam format (.csv)".
  * Upload Card: Icon ilustrasi upload cloud, file input picker (`.csv`), dan tombol "Import Dataset".
  * Validasi: Pemeriksaan format ekstensi file dan struktur kolom komentar.

### Screen 5: Dashboard Sentimen (`{{DATA:SCREEN:SCREEN_7}}`)
* **Role:** Ringkasan analitik dan metrik utama dataset.
* **Key Components:**
  * Sidebar Navigasi: Logo, Menu Utama (*Dashboard*, *Preprocessing*, *Klasifikasi*, *Testing*, *Logout*).
  * Metrik Ringkasan (KPI Cards):
    * **Total Dataset:** misal `1.000` data komentar.
    * **Nama Dataset Aktif:** `komentar_youtube.csv`.
    * **Aksi Cepat:** Tautan langsung ke "Upload Dataset" beserta indikator status koneksi.
  * Visualisasi Data: Diagram batang distribusi sentimen (*Positif*, *Negatif*, *Netral*) dengan baseline grid dan legenda.

### Screen 6: Preprocessing Pipeline (`{{DATA:SCREEN:SCREEN_5}}`)
* **Role:** Visualisasi dan eksekusi tahapan pembersihan data teks.
* **Key Stages:**
  1. **Hapus Karakter Spesial:** Menghapus emoji, tanda baca, simbol, hyperlink, dan username mention.
  2. **Case Folding (Lowercase):** Konversi seluruh teks menjadi huruf kecil seragam.
  3. **Stopword Removal:** Eliminasi kata hubung dan kata umum yang minim nilai analisis informatif (Bahasa Indonesia).
  4. **Stemming (Sastrawi):** Reduksi kata berimbuhan ke kata dasar.
* **Action:** Tombol "Lanjut ke Klasifikasi" setelah proses pembersihan selesai.

### Screen 7: Klasifikasi & Pelatihan Model (`{{DATA:SCREEN:SCREEN_3}}`)
* **Role:** Pipeline pemodelan Machine Learning menggunakan Support Vector Machine.
* **Key Steps:**
  * **Langkah 1 (TF-IDF):** Pembobotan frekuensi istilah dan invers frekuensi dokumen untuk representasi vektor numerik.
  * **Langkah 2 (Split Data):** Pemisahan data training dan validation/testing (misal 80:20 atau 70:30).
  * **Langkah 3 (Training SVM):** Pelatihan algoritma SVM (linear kernel / RBF kernel).
  * **Pengujian & Evaluasi:** Perhitungan Confusion Matrix, Akurasi, Precision, Recall, dan F1-Score.

### Screen 8: Testing Model & Inferensi (`{{DATA:SCREEN:SCREEN_1}}`)
* **Role:** Antarmuka pengujian model terdistribusi untuk pengguna akhir.
* **Key Components:**
  * **Section 1 - Cek Kalimat Baru (Single Testing):**
    * Textarea input komentar baru bebas.
    * Tombol "Jalankan Prediksi" untuk melihat label sentimen seketika.
  * **Section 2 - Cek Data Testing (Batch Testing CSV):**
    * Pilihan preset (e.g. 100 Data Testing B.Indo).
    * File picker untuk upload file pengujian CSV mandiri + tombol "Upload & Prediksi CSV".
    * Kartu hitung hasil: Positif, Netral, Negatif, Total Data.
    * Tabel hasil prediksi teks dan kelas sentimen yang dihasilkan.

---

## 5. Non-Functional Requirements & Design Principles

* **Design Aesthetic:** Minimalis, clean, monokromatik (hitam, putih, abu-abu slate) dengan kontras tinggi untuk kenyamanan membaca teks panjang dan data tabular.
* **Responsiveness:** Dioptimalkan untuk layar Desktop (resolusi standar 1280px - 1440px+).
* **Usability & Accessibility:** Visual hierarchy yang jelas dengan pembagian langkah kerja bertahap (*stepped wizard process*) agar user non-teknis mudah mengikuti alur data science.
