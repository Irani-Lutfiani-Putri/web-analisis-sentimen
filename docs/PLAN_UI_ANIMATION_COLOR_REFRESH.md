# PLAN IMPLEMENTASI — UI COLOR & INTERACTION REFRESH

**Project:** `web-analisis-sentimen`
**Tujuan:** Memperbarui palet warna, animasi hover, micro-interactions, dan state visual pada **seluruh halaman** tanpa mengubah layout website yang sudah ada.

---

## 0. Aturan Utama (Wajib Dipatuhi)

1. **Jangan mengubah layout.** Pertahankan struktur halaman, susunan/urutan elemen, grid, ukuran dan posisi panel, spacing, dimensi komponen, hirarki informasi, navigasi, breakpoint/responsivitas, serta alur UX yang sekarang.
2. **Jangan menghapus atau mengganti fitur.** Seluruh fungsi, route, API call, validasi, proses upload, analisis, tabel, grafik, filter, dan autentikasi harus tetap berjalan seperti semula.
3. **Scope hanya visual dan interaksi:** warna, token desain, border, shadow, state hover/focus/active/disabled/loading, dan animasi kecil yang membantu feedback pengguna.
4. Terapkan perubahan secara konsisten ke **semua halaman/route yang benar-benar ada di project**, bukan hanya dashboard atau halaman utama. Audit daftar halaman terlebih dahulu; jangan berasumsi semua halaman yang disebut di dokumen ini sudah tersedia.
5. **Jangan membuat ulang desain dari nol.** Gunakan komponen yang ada. Refactor komponen bersama hanya bila diperlukan untuk konsistensi visual, tanpa mengubah markup/struktur layout lebih dari yang diperlukan.
6. Jangan menambahkan animasi dekoratif berlebihan. UI harus tetap terasa profesional, jelas, cepat, dan nyaman untuk aplikasi analisis data.
7. Jangan mengubah konten, label, istilah, urutan aksi, maupun copywriting kecuali ada bug yang menghalangi fungsi dan perubahan tersebut mendapat alasan teknis yang jelas.

### Definisi “layout tetap sama”
- Posisi dan urutan konten tidak berubah.
- Lebar/tinggi panel, ukuran kartu, kolom tabel, grid, padding, margin, dan jarak antarbagian tetap menggunakan nilai yang sekarang.
- Sidebar, header/topbar, footer, modal, serta posisi tombol tidak dipindahkan.
- Tidak menambahkan section baru, menghapus section, atau mengubah pola navigasi.
- Pada hover/focus, perubahan visual tidak boleh mendorong konten lain atau menyebabkan layout shift.
- Perubahan ukuran hanya diperbolehkan jika diperlukan untuk mempertahankan keterbacaan/aksesibilitas, dan harus seminimal mungkin serta dicatat.

---

## PHASE 1 — Audit Project dan Baseline

### Tugas agent
1. Baca struktur project, `package.json`, konfigurasi CSS/Tailwind, theme provider, dan komponen UI bersama.
2. Identifikasi framework serta sistem styling yang benar-benar dipakai. Jangan mengasumsikan project menggunakan React/Tailwind bila belum diverifikasi.
3. Petakan semua route/page dan shared component. Catat juga halaman autentikasi, modal, drawer, dropdown, toast, dialog, empty state, error state, dan loading state yang tersedia.
4. Temukan warna hard-coded, class warna yang berulang, style inline, gradient, shadow, border, dan hover state yang sekarang digunakan.
5. Ambil screenshot atau catat tampilan awal setiap halaman pada ukuran desktop dan mobile sebagai pembanding visual.
6. Catat cara menjalankan project, test, lint, dan build. Jalankan baseline test/build sebelum melakukan perubahan jika environment memungkinkan.

### Output
- Daftar halaman/route yang ditemukan.
- Daftar shared component yang perlu diperbarui.
- Ringkasan styling dan library animasi yang sudah terpasang.
- Baseline screenshot atau catatan masalah visual.

### Kriteria selesai
Tidak ada perubahan kode visual sebelum audit selesai. Seluruh route yang ditemukan masuk ke checklist implementasi berikutnya.

---

## PHASE 2 — Terapkan Design Tokens dan Palet Warna

Gunakan palet berikut di seluruh halaman. Warna utama harus dominan, sedangkan warna lainnya menjadi aksen pendukung.

| Token | Hex | Peran |
|---|---|---|
| `--color-primary` | `#F13E93` | Warna brand utama: CTA, indikator aktif, link penting, focus ring, elemen utama terpilih |
| `--color-primary-soft` | `#F891BB` | Hover/gradient pendukung, highlight lembut, dekorasi kecil |
| `--color-pink-blush` | `#F9D0CD` | Background lembut, permukaan sekunder, badge atau highlight yang tidak dominan |
| `--color-lime-soft` | `#FAFFCB` | Aksen kontras yang hemat: status tertentu, highlight kecil, atau dekorasi; bukan warna utama seluruh halaman |

### Aturan pemakaian warna
- `#F13E93` adalah **warna brand dominan**, tetapi jangan membuat semua background menjadi pink solid. Pertahankan hierarki permukaan dan netral yang sudah ada pada website.
- Gunakan warna netral yang sudah ada untuk teks utama, background halaman, garis pemisah, dan permukaan tabel selama masih sesuai desain saat ini.
- Gunakan `#F891BB` untuk transisi/hover dan aksen pendamping, bukan menggantikan semua warna primary.
- Gunakan `#F9D0CD` untuk permukaan lembut. Pastikan teks di atasnya tetap terbaca.
- Gunakan `#FAFFCB` secara terbatas sebagai aksen. Jangan menjadikannya background besar pada banyak komponen sekaligus.
- Jangan memakai warna brand untuk seluruh teks panjang. Teks isi tetap memakai warna teks yang mudah dibaca.
- Pastikan status sukses, warning, error, dan informasi tetap dapat dibedakan. Jangan mengganti semua warna status semantik menjadi pink; pertahankan makna status dan perbaiki keselarasan tampilannya dengan palet brand.
- Buat token untuk varian hover, active, subtle background, border, focus ring, dan shadow bila pola tersebut memang dipakai pada project.
- Hindari menyebarkan kode hex baru di banyak file. Utamakan CSS variables, theme configuration, atau design tokens yang sesuai dengan arsitektur saat ini.

### Contoh token CSS (sesuaikan dengan stack project)
```css
:root {
  --color-primary: #F13E93;
  --color-primary-soft: #F891BB;
  --color-pink-blush: #F9D0CD;
  --color-lime-soft: #FAFFCB;

  /* Buat token berikut berdasarkan warna netral yang sudah ada pada website. */
  --color-primary-hover: #d92f7f;
  --color-primary-active: #c92771;
  --color-primary-tint: rgba(241, 62, 147, 0.10);
  --color-primary-border: rgba(241, 62, 147, 0.28);
  --shadow-brand: 0 6px 20px rgba(241, 62, 147, 0.14);

  --motion-fast: 140ms;
  --motion-normal: 200ms;
  --motion-slow: 280ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
}
```

> Catatan: token hover di atas adalah titik awal. Validasi hasilnya terhadap warna, contrast, dan tema project sebelum menjadikannya final. Jangan memaksakan token jika sistem theme yang ada sudah menyediakan pola lebih tepat.

### Kriteria selesai
- Seluruh warna brand menggunakan token terpusat.
- Tidak ada warna pink/aksen baru yang dibuat secara acak di tiap halaman.
- Tampilan netral, hierarki konten, dan identitas masing-masing halaman tetap terjaga.
- Kontras teks dan kontrol diperiksa, terutama tombol, badge, teks di atas background pastel, serta state disabled.

---

## PHASE 3 — Standarisasi Hover dan Micro-interactions

Buat pola interaksi yang konsisten untuk jenis komponen yang sama. Gunakan CSS transition untuk perubahan visual sederhana. Animasi harus terasa cepat dan tidak menghalangi tindakan pengguna.

### A. Button dan CTA
- **Primary button:** gunakan `#F13E93` sebagai warna utama; hover dapat menjadi warna primary yang sedikit lebih gelap atau memakai aksen soft secara terkontrol.
- Tambahkan transisi ringan untuk warna, border, dan shadow.
- Active/pressed memberi feedback kecil tanpa menggeser elemen lain.
- Loading dan disabled harus memiliki visual yang jelas; jangan memalsukan keberhasilan aksi.
- Jangan menerapkan hover yang membuat tombol berubah ukuran atau berpindah posisi.

### B. Card dan panel statistik
- Hover: border lebih terlihat, shadow lembut, atau tint pink tipis.
- Elevasi hanya boleh sangat kecil jika sesuai dengan perilaku card yang ada. Jika card bukan elemen yang dapat diklik, jangan membuatnya terlihat seolah-olah tombol.
- Angka statistik boleh menggunakan animasi count-up **hanya jika** nilainya final, animasinya tidak menyesatkan, dan tidak mengganggu pembacaan. Ini opsional, bukan default.

### C. Link dan navigasi
- Tautan dapat menggunakan transisi warna dan underline yang halus.
- Item sidebar aktif harus tetap jelas setelah pointer meninggalkan item.
- Hover item navigasi tidak boleh mengubah lebar sidebar atau posisi label/icon.
- Pertahankan route, urutan menu, ikon, serta cara navigasi saat ini.

### D. Input, select, search, dan textarea
- Hover: border sedikit menguat jika relevan.
- Focus: tampilkan focus ring yang terlihat dan konsisten dengan `#F13E93`.
- Error/invalid: pertahankan indikator error dengan pesan yang sudah ada.
- Jangan mengandalkan warna saja untuk menunjukkan error, selected, atau focus.
- Transisi fokus jangan membuat ukuran input berubah dan menggeser layout.

### E. Modal, dropdown, popover, tooltip, dan toast
- Gunakan fade singkat dan, bila cocok, gerakan kecil saat elemen muncul/hilang.
- Pertahankan ukuran, posisi, backdrop, urutan tumpukan, keyboard behavior, dan cara menutup modal saat ini.
- Hindari animasi modal yang lama, bouncing, atau zoom berlebihan.
- Jangan menambahkan tooltip pada semua elemen jika tidak diperlukan.

### F. Tabel dan daftar komentar
- Hover row: gunakan highlight tipis, misalnya tint dari primary, selama tidak mengurangi keterbacaan teks.
- Pertahankan ukuran kolom, tinggi baris, sorting, pagination, filter, selection, dan responsivitas.
- Bedakan hover row dari row terpilih dan dari status sentimen.
- Jangan menambahkan animasi per karakter pada teks komentar.

### G. Upload, proses analisis, dan hasil
- Area upload boleh menampilkan border/background interaktif saat drag-over jika dropzone sudah ada.
- Loading/progress harus mencerminkan proses asli. Jangan membuat persentase atau animasi yang memberi kesan proses selesai padahal belum.
- Hasil analisis boleh muncul dengan fade singkat tanpa mengubah urutan komponen atau menggeser layout secara mencolok.
- Grafik hanya boleh dianimasikan menggunakan API/library grafik yang sudah terpasang, jika didukung tanpa merusak interaksi dan aksesibilitas.

### H. Icon dan elemen kecil
- Icon interaktif boleh berubah warna atau bergerak sedikit; batasi gerakan dan pastikan fungsi icon tidak berubah.
- Jangan menerapkan rotasi/scale pada semua icon secara membabi buta.
- Elemen dekoratif tidak boleh mengganggu area klik.

### Durasi dan karakter gerakan
- Hover/focus: sekitar `140–200ms`.
- Dropdown/popover/modal: sekitar `180–280ms`.
- Gunakan easing halus; hindari animasi lambat, bounce berlebihan, flash, dan efek yang membuat aplikasi terasa seperti landing page promosi.
- Gunakan `transform` dan `opacity` bila memungkinkan agar animasi tidak memicu layout recalculation berlebihan.

### Kriteria selesai
Semua jenis komponen memiliki state default, hover, active, focus-visible, disabled, serta loading/error bila relevan. Interaksi konsisten lintas halaman dan tidak menimbulkan layout shift.

---

## PHASE 4 — Putuskan Penggunaan Library Animasi

### Urutan keputusan
1. **Periksa dependency yang sudah tersedia.** Jika library animasi sudah ada dan masih sesuai, prioritaskan itu.
2. Untuk efek sederhana seperti perubahan warna, border, opacity, shadow, underline, dan hover, gunakan **CSS**. Jangan menambahkan library hanya untuk efek CSS dasar.
3. Jika project berbasis React dan membutuhkan entrance/exit animation yang kompleks pada modal, dropdown, atau komponen yang mount/unmount, pertimbangkan library Motion yang kompatibel dengan versi React/project saat ini. Verifikasi dokumentasi, versi package, dan pola import sebelum instalasi.
4. Untuk animasi timeline/scroll yang benar-benar kompleks, library seperti GSAP hanya boleh dipertimbangkan bila kebutuhan jelas. Jangan memasangnya hanya demi hover button atau card.
5. Jika project bukan React, pilih solusi yang sesuai dengan framework yang ditemukan saat audit; jangan menambah dependency yang tidak relevan.

### Batasan library
- Jangan memasang dua library animasi dengan fungsi yang tumpang tindih.
- Jangan mengubah framework, router, state management, chart library, atau build tool hanya demi efek visual.
- Jangan menggunakan JavaScript untuk animasi yang dapat diselesaikan dengan CSS sederhana.
- Catat library baru, alasan penambahan, ukuran/dependency impact jika dapat diperiksa, serta cara menghapusnya jika tidak diperlukan.

### Kriteria selesai
Dependency baru hanya digunakan bila ada kebutuhan animasi yang terukur dan tidak bisa diselesaikan secara lebih sederhana dengan teknologi yang sudah ada.

---

## PHASE 5 — Terapkan ke Seluruh Halaman tanpa Mengubah Layout

Gunakan daftar halaman hasil audit pada Phase 1. Terapkan token dan interaksi melalui shared component lebih dulu, lalu lakukan penyesuaian khusus per halaman.

### Cakupan pemeriksaan halaman
Checklist ini adalah contoh area pemeriksaan; gunakan hanya halaman/fitur yang memang ada di project.

- [ ] Login / autentikasi
- [ ] Modal atau langkah awal upload dataset
- [ ] Dashboard
- [ ] Upload dataset / import file
- [ ] Preview dataset dan tabel komentar
- [ ] Konfigurasi atau proses analisis sentimen
- [ ] Halaman hasil analisis
- [ ] Ringkasan/grafik distribusi sentimen
- [ ] Detail hasil atau detail dataset
- [ ] Riwayat analisis
- [ ] Filter, search, sort, pagination
- [ ] Pengaturan / profil / akun
- [ ] Dialog konfirmasi, modal, dropdown, tooltip, toast
- [ ] Empty state, loading state, error state, success state
- [ ] Halaman tambahan dan route lain yang ditemukan saat audit

### Cara implementasi
1. Mulai dari theme/token dan shared component agar warna serta transisi tidak didefinisikan ulang pada setiap page.
2. Periksa tiap halaman memakai baseline screenshot. Ubah style tanpa memindahkan elemen.
3. Pastikan modal awal, upload flow, dashboard, dan alur analisis tetap persis sama dari sisi urutan dan perilaku.
4. Periksa state tiap halaman, bukan hanya tampilan default.
5. Jangan menambahkan page baru, section baru, banner baru, atau dekorasi besar yang mengubah komposisi visual.
6. Jika sebuah komponen punya style unik karena makna fungsional, pertahankan makna tersebut; selaraskan hanya warna dan motion-nya.

### Kriteria selesai
Seluruh route yang ada telah ditinjau dan menerapkan sistem warna/interaksi baru secara konsisten, sementara struktur layout dan UX tetap sama.

---

## PHASE 6 — Aksesibilitas, Responsivitas, dan Performa

### Aksesibilitas
- Hormati preferensi sistem `prefers-reduced-motion: reduce`. Kurangi/nonaktifkan gerakan yang tidak penting saat preferensi ini aktif.
- Semua kontrol harus dapat digunakan dengan keyboard seperti sebelumnya.
- Gunakan `:focus-visible` atau pola yang setara; jangan menghapus outline tanpa pengganti yang jelas.
- Hover bukan satu-satunya cara untuk menampilkan informasi atau state.
- Pastikan kontras teks, label, icon, border input, dan focus ring tetap memadai.
- Jangan memakai animasi berkedip, flashing, parallax agresif, atau gerakan terus-menerus yang tidak diperlukan.

### Responsivitas
- Periksa desktop, tablet, dan mobile.
- Pada perangkat touch, jangan membuat fungsi inti hanya muncul saat hover.
- Tidak boleh ada horizontal overflow baru, komponen berpindah, atau teks terpotong akibat perubahan style.
- Pertahankan breakpoint dan behavior responsif yang sudah ada.

### Performa
- Utamakan CSS transition untuk interaksi ringan.
- Hindari animasi layout property seperti `width`, `height`, `top`, dan `left` jika dapat dicapai dengan transform/opacity.
- Hindari listener mouse global atau requestAnimationFrame yang tidak diperlukan.
- Bersihkan listener/timer pada unmount bila ada animasi JavaScript yang menggunakannya.
- Jangan menambahkan efek blur besar atau shadow berat pada banyak elemen sekaligus tanpa alasan.

### Kriteria selesai
Tidak ada penurunan fungsi keyboard/touch, layout shift, overflow baru, atau masalah performa yang terlihat. Preferensi reduced-motion dihormati.

---

## PHASE 7 — QA, Regression Check, dan Penyerahan

### Visual QA
- [ ] Bandingkan screenshot sebelum/sesudah per halaman pada viewport yang sama.
- [ ] Konfirmasi susunan dan ukuran layout tetap sama.
- [ ] Pastikan warna primary `#F13E93` paling menonjol, sedangkan `#F891BB`, `#F9D0CD`, dan `#FAFFCB` digunakan sebagai pendukung secara terkontrol.
- [ ] Periksa hover pada mouse dan focus state dengan keyboard.
- [ ] Periksa state active, disabled, loading, selected, error, empty, dan success yang tersedia.
- [ ] Pastikan perubahan hover tidak menyebabkan teks bergeser, tombol berubah ukuran, atau layout melompat.

### Functional regression
- [ ] Login/logout dan navigasi route tetap bekerja.
- [ ] Upload file dan validasi tetap bekerja.
- [ ] Proses analisis tetap berjalan.
- [ ] Tombol, link, dropdown, modal, tab, search, filter, sort, dan pagination tetap bekerja.
- [ ] Dataset, label sentimen, angka, grafik, serta output hasil tidak berubah akibat implementasi styling.
- [ ] Tidak ada error console/import/dependency.
- [ ] Lint, test, dan build dijalankan sesuai script yang tersedia di project.

### Penyerahan agent
Laporkan:
1. Halaman dan shared component yang telah diperbarui.
2. File yang diubah.
3. Palet/token yang dibuat dan cara pemakaiannya.
4. Jenis animasi/interaksi yang diterapkan per komponen.
5. Library baru yang ditambahkan (jika ada), beserta alasan teknisnya.
6. Hasil lint/test/build yang benar-benar dijalankan.
7. Daftar masalah yang belum selesai atau keterbatasan environment.
8. Konfirmasi eksplisit bahwa layout, route, fitur, dan alur UX tidak diubah.

---

## Urutan Eksekusi yang Disarankan

1. Phase 1 — Audit dan baseline.
2. Phase 2 — Design tokens/palet.
3. Phase 3 — Hover dan micro-interactions pada shared component.
4. Phase 4 — Keputusan library hanya jika diperlukan.
5. Phase 5 — Penerapan pada setiap halaman yang ada.
6. Phase 6 — Aksesibilitas, responsivitas, performa.
7. Phase 7 — QA dan laporan.

Jalankan secara berurutan. Jangan langsung mengubah semua halaman tanpa audit dan baseline.

## Instruksi Final untuk Agent

**Lakukan visual refresh pada seluruh halaman website menggunakan palet `#F13E93`, `#F891BB`, `#F9D0CD`, dan `#FAFFCB`. Fokuskan perubahan pada warna, hover, focus/active states, transisi, dan micro-interactions. Pertahankan layout, ukuran, posisi, urutan komponen, navigasi, route, konten, responsivitas, dan seluruh alur UX yang sudah ada. Audit project sebelum coding, gunakan CSS atau dependency yang sudah tersedia terlebih dahulu, tambahkan library hanya jika memang dibutuhkan, kemudian uji semua halaman dan fitur sebelum menyatakan selesai.**
