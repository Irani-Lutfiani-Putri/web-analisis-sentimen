# Alur Role — Pengguna Biasa vs Superadmin

Dokumen ini merangkum siapa boleh melihat dan melakukan apa, beserta aturan yang menjaga integritas data penelitian. Rujukan aturan: `STRICT.md` §C3 (label manual tidak boleh ditimpa lexicon), §C5 (tidak memaksa Netral), §D6 (role tidak diterima dari request), §E4–E6 (holdout independen).

## Ringkasan

| Kemampuan | `user` | `superadmin` | Dijaga di |
|---|---|---|---|
| Registrasi mandiri (`/register`) | ✅ selalu jadi `user` | ❌ hanya lewat CLI `create-superadmin` | `app/routes/auth.py` |
| Import CSV | ✅ | ✅ | `app/routes/datasets.py` |
| Import CSV dengan kolom label manual | ❌ 403 | ✅ | `app/routes/datasets.py:27` |
| Pelabelan lexicon otomatis saat import | ✅ otomatis | ✅ otomatis | `app/routes/datasets.py:_start_auto_lexicon` |
| Jalankan ulang lexicon dari UI | ❌ tombol tidak dirender | ✅ | `app/templates/preprocessing/index.html` |
| Preprocessing teks (Sastari) | ✅ | ✅ | `app/routes/preprocessing.py:run_preprocessing` |
| Filter label | 5 opsi | 8 opsi | `app/services/comment_query.py` |
| Melihat baris `review` | ❌ disaring di SQL | ✅ | `comment_query.build_query` |
| Kolom Sumber / Skor / Review | ❌ tidak dikirim ke HTML | ✅ | `_index_context` |
| Beri label manual | ❌ 403 | ✅ | `@superadmin_required` |
| Tandai/lepas data uji independen | ❌ 403 | ✅ | `holdout_service.set_holdout` |
| Halaman **Kelola Dataset** | ❌ 403, menu tidak tampil | ✅ | `app/routes/admin_datasets.py` |
| Latih SVM | ⚠️ butuh holdout (yang hanya bisa dibuat Superadmin) | ✅ | `app/services/classification_service.py` |

## Filter label

| Nilai | Arti | `user` | `superadmin` |
|---|---|---|---|
| `semua` | semua baris yang boleh dilihat role tersebut | ✅ | ✅ |
| `sudah` | `sentiment_label` sudah terisi | ✅ | ✅ |
| `positif` / `negatif` / `netral` | label akhir sama dengan nilai itu | ✅ | ✅ |
| `review` | `review_status = 'review'` (menunggu peninjauan) | ❌ | ✅ |
| `manual` | `label_source = 'manual'` | ❌ | ✅ |
| `lexicon` | `label_source = 'lexicon'` | ❌ | ✅ |

Nilai filter yang tidak diizinkan untuk role tersebut **tidak** menghasilkan 403; filter jatuh ke `semua` agar URL lama atau tautan yang dibagikan tetap berfungsi. Penyaringan baris `review` dilakukan di query SQL (`coalesce(review_status,'') != 'review'`) sehingga jumlah baris dan jumlah halaman konsisten dengan yang benar-benar ditampilkan.

## Tiga jenis label yang tidak boleh tercampur

| Kolom | Diisi oleh | Boleh ditimpa? |
|---|---|---|
| `lexicon_label` | kamus InSet saat pelabelan otomatis | ya, saat lexicon dijalankan ulang |
| `sentiment_label` | lexicon (otomatis) atau manual (Superadmin) | ya, tapi hanya oleh Superadmin lewat label manual |
| `manual_label` | Superadmin (form atau kolom CSV) | hanya oleh Superadmin; **tidak pernah** oleh lexicon |

`annotate_dataset()` melewati baris yang sudah punya `manual_label` (`app/services/lexicon_service.py:89-92`). Konsekuensinya, menjalankan ulang lexicon tidak akan menghapus keputusan manusia — inilah aturan yang diuji oleh `tests/test_auto_lexicon.py::test_imported_manual_labels_are_never_overwritten`.

## Status baris (`review_status`)

| Nilai | Arti | Terlihat oleh `user` |
|---|---|---|
| `accepted` | lexicon yakin (skor ≠ 0, tanpa negasi, tanpa polaritas campur) | ✅ |
| `review` | ambigu: tidak ada kata kamus, skor 0, ada negasi, atau polaritas campur | ❌ |
| `resolved` | sudah diberi label manual oleh Superadmin | ✅ |
| `NULL` | baris hasil impor berlabel manual | ✅ |

## Pop-up progres

Setiap tombol ber-`data-progress="Judul"` membuka satu `<dialog>` saat form dikirim (`app/static/js/progress-dialog.js`). Untuk job background (`lexicon`, `preprocessing`), dialog memantau `GET /preprocessing/jobs/<job_id>` setiap 800 ms dan menampilkan `selesai/total` dari penghitung worker yang sebenarnya — bukan animasi palsu. Bila JavaScript mati, halaman tetap berfungsi: panel status server-side dan hasil tabel tetap dirender.
