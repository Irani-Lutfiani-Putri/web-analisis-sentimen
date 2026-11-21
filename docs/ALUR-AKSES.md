# Alur Akses Tanpa Role

Dokumen ini merangkum siapa boleh melihat dan melakukan apa. Tidak ada role `superadmin`, `admin`, atau `user`. Register membuat akun, lalu pengguna login dengan akun itu. Semua akun setara dan hanya melihat dataset miliknya sendiri.

Rujukan aturan riset: `STRICT.md` §C3 (label manual tidak boleh ditimpa lexicon), §C5 (tidak memaksa Netral), §E4–E6 (holdout independen).

## Ringkasan

| Kemampuan | Akun |
|---|---|
| Registrasi mandiri (`/register`) | ya |
| Login | ya, memakai akun yang sudah diregister |
| Impor CSV | ya |
| Impor kolom label manual | ya |
| Pelabelan lexicon otomatis saat import | ya, otomatis |
| Hitung ulang label otomatis | ya, tombol **Hitung Ulang Label Otomatis** |
| Preprocessing teks (Sastrawi) | ya |
| Melihat baris review dan baris tanpa label | ya, di `/labels` |
| Melihat baris review di Preprocessing | tidak |
| Filter label di Preprocessing | Semua, Sudah dilabelkan, Positif, Negatif, Netral |
| Filter di `/labels` | Semua, Perlu label, Sudah dilabelkan, Positif, Negatif, Netral, Label manual, Label otomatis |
| Memberi label manual | ya, untuk dataset sendiri |
| Menandai atau melepas holdout | ya, untuk dataset sendiri |
| Melatih SVM | ya, setelah holdout tiga kelas |
| Melihat metadata label | ya, di `/labels` untuk dataset sendiri |

## Register dan login

1. Buka `/register`.
2. Isi nama, email, dan password minimal 12 karakter.
3. Setelah register, aplikasi mengarahkan ke `/login`.
4. Login dengan email dan password yang baru dibuat.
5. Setiap akun hanya dapat membuka dataset, komentar, model, dan prediksi miliknya.

## Preprocessing

Preprocessing hanya menampilkan komentar yang sudah punya label akhir:

```sql
sentiment_label IS NOT NULL
AND coalesce(review_status, '') != 'review'
```

Baris review dan baris tanpa label tidak muncul. Halaman menampilkan jumlah baris yang menunggu dan tautan **Buka Review dan Label**.

Tombol **Hitung Ulang Label Otomatis** tersedia untuk semua akun. Teks pendamping menjelaskan bahwa label manual tidak berubah.

## Halaman Review dan Label

Halaman `/labels` tidak ada di sidebar. Halaman ini dipakai untuk:

- melihat baris yang perlu label,
- memberi label manual satu per satu atau massal,
- menandai atau melepas holdout.

Default filter adalah **Perlu label**, yang mencakup:

```sql
sentiment_label IS NULL OR review_status = 'review'
```

## Tiga jenis label yang tidak boleh tercampur

| Kolom | Diisi oleh | Boleh ditimpa? |
|---|---|---|
| `lexicon_label` | kamus InSet saat pelabelan otomatis | ya, saat label otomatis dihitung ulang |
| `sentiment_label` | lexicon atau manual | ya, lewat label manual |
| `manual_label` | pengguna lewat form atau CSV | hanya lewat label manual; **tidak pernah** oleh lexicon |

`annotate_dataset()` melewati baris yang sudah punya `manual_label` (`app/services/lexicon_service.py`). Menjalankan ulang label otomatis tidak menghapus keputusan manusia.

## Status baris (`review_status`)

| Nilai | Arti | Terlihat di Preprocessing |
|---|---|---|
| `accepted` | lexicon yakin (skor bukan nol, tanpa negasi, tanpa polaritas campur) | ya |
| `review` | ambigu: tidak ada kata kamus, skor nol, ada negasi, atau polaritas campur | tidak, hanya di `/labels` |
| `resolved` | sudah diberi label manual | ya |
| `NULL` | baris hasil impor berlabel manual | ya |

## Holdout dan training

1. Beri label manual pada komentar di `/labels`.
2. Tandai komentar sebagai data uji independen.
3. Pastikan Positif, Negatif, dan Netral masing-masing terwakili.
4. Jalankan training dari halaman Klasifikasi.
5. Lepas tanda holdout bila komentar tidak lagi dipakai sebagai data uji.

## Pop-up progres

Setiap tombol ber-`data-progress="Judul"` membuka satu `<dialog>` saat form dikirim (`app/static/js/progress-dialog.js`). Untuk job background (label otomatis dan preprocessing), dialog memantau `GET /preprocessing/jobs/<job_id>` setiap 800 ms dan menampilkan `selesai/total` dari penghitung worker yang sebenarnya. Bila JavaScript mati, halaman tetap berfungsi dan hasil tabel tetap dirender.
