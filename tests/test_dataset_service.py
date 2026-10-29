import io
import pytest
from app.services.dataset_service import parse_csv, DatasetError


def test_valid_csv_maps_comment_and_manual_label():
    rows, info = parse_csv(io.BytesIO('isi,kategori\n"Tambang berdampak",Negatif\n"Operasi tambang",Netral\n'.encode()), 'isi', 'kategori')
    assert rows == [(2, 'Tambang berdampak', 'Negatif'), (3, 'Operasi tambang', 'Netral')]
    assert info['accepted'] == 2
    assert info['rejected'] == 0
    assert info['columns'] == ['isi', 'kategori']


def test_semicolon_delimited_csv_is_accepted():
    rows, info = parse_csv(io.BytesIO('"Username";"Isi Komentar"\n"@akun";"Tambang memberi manfaat"\n'.encode()), 'Isi Komentar', None)
    assert rows == [(2, 'Tambang memberi manfaat', None)]
    assert info['accepted'] == 1
    assert info['columns'] == ['Username', 'Isi Komentar']


def test_invalid_utf8_rejected():
    with pytest.raises(DatasetError, match='UTF-8'):
        parse_csv(io.BytesIO(b'isi\n\xff'), 'isi', None)


def test_missing_comment_column_rejected():
    with pytest.raises(DatasetError, match='Kolom komentar') as caught:
        parse_csv(io.BytesIO(b'isi\nTeks'), 'komentar', None)
    assert caught.value.field == 'comment_column'


def test_invalid_utf8_identifies_file_field():
    with pytest.raises(DatasetError) as caught:
        parse_csv(io.BytesIO(b'isi\n\xff'), 'isi', None)
    assert caught.value.field == 'file'


def test_empty_and_invalid_label_rows_reported():
    rows, info = parse_csv(io.BytesIO(b'isi,kategori\n,Kosong\nTambang,Salah\nBagus,Positif'), 'isi', 'kategori')
    assert rows == [(4, 'Bagus', 'Positif')]
    assert info['rejected'] == 2
    assert info['accepted'] == 1
