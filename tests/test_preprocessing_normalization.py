import os

import pytest

from app.services import normalization
from app.services.preprocessing_service import preprocess_text, preprocessing_version, transform_stages


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("KENAPA tambangnya hannya merusak bumi???", "kenapa tambang hanya rusak bumi"),
        ("TeteP aja kalian merusak bumi cuk", "tetap kalian rusak bumi cuk"),
        ("pasir itu ekspor saja ke singapura ...... gkgkgk", "pasir ekspor singapura"),
        ("Freeport bagus banget pengelolaan tambangnya!", "freeport bagus banget kelola tambang"),
        ("gk setuju kalau lingkungan dirusak", "tidak setuju lingkungan rusak"),
    ],
)
def test_required_examples(raw, expected):
    assert preprocess_text(raw) == expected


def test_stages_are_sequential_and_inspectable():
    stages = transform_stages("KENAPA tambangnya hannya merusak bumi???")
    assert stages["cleaning"] == "KENAPA tambangnya hannya merusak bumi"
    assert stages["case_folding"] == "kenapa tambangnya hannya merusak bumi"
    assert stages["tokenizing"] == "kenapa | tambangnya | hannya | merusak | bumi"
    assert stages["normalization"] == "kenapa tambangnya hanya merusak bumi"
    assert stages["stopword"] == "kenapa tambangnya hanya merusak bumi"
    assert stages["stemming"] == "kenapa tambang hanya rusak bumi"


def test_noise_is_removed_without_harming_laughter_or_short_words():
    assert preprocess_text("aaaaaa") == ""
    assert preprocess_text("kkkkkk") == ""
    assert preprocess_text("zzzz") == ""
    assert preprocess_text("gkgkgk ......") == ""
    assert preprocess_text("wkwk") == "wkwk"
    assert preprocess_text("hahaha") == "hahaha"
    assert preprocess_text("bagus") == "bagus"
    assert preprocess_text("cuk") == "cuk"


def test_negations_survive_normalization_and_stemming():
    assert preprocess_text("gk setuju kalau lingkungan dirusak") == "tidak setuju lingkungan rusak"
    assert preprocess_text("tidak bagus") == "tidak bagus"
    assert preprocess_text("jangan merusak lingkungan") == "jangan rusak lingkungan"
    assert preprocess_text("belum ada pengelolaan yang baik") == "belum kelola baik"
    assert preprocess_text("bukan bagus") == "bukan bagus"
    assert preprocess_text("belum selesai") == "belum selesai"
    assert preprocess_text("jangan rusak") == "jangan rusak"


def test_short_meaningful_words_survive():
    for word in ("bagus", "buruk", "setuju", "tidak", "parah", "mantap", "kecewa", "rusak", "amat"):
        assert preprocess_text(word) == word


def test_special_terms_and_company_names_are_preserved():
    assert preprocess_text("pertambangan Freeport di Papua") == "tambang freeport papua"
    assert preprocess_text("PT Freeport Indonesia") == "pt freeport indonesia"
    assert preprocess_text("tailing dan amdal") == "tailing amdal"
    assert preprocess_text("Grasberg dan Gresik") == "grasberg gresik"
    assert preprocess_text("Smelter dan tailing") == "smelter tailing"
    assert preprocess_text("telung") == "telung"
    assert preprocess_text("kerusakan") == "rusak"
    assert preprocess_text("perusakan pengrusakan") == "rusak rusak"
    assert preprocess_text("pemerintahan pejabat") == "pemerintah pejabat"
    assert preprocess_text("tujuan menuju perampokan menguras") == "tujuan menuju rampok kuras"
    assert preprocess_text("lainnya lainya memilukan") == "lain lain pilu"


def test_cleaning_removes_symbols_html_and_mentions():
    assert preprocess_text("<b>bagus</b> @user!!! ???") == "bagus"
    assert preprocess_text("bagus × jelek") == "bagus jelek"
    assert preprocess_text("bagus 123 jelek") == "bagus jelek"


def test_number_units_are_removed_as_whole_expressions():
    assert preprocess_text("7m") == ""
    assert preprocess_text("10 ton") == ""
    assert preprocess_text("7 m") == ""
    assert preprocess_text("2.000 ton") == ""
    assert preprocess_text("100%") == ""
    assert preprocess_text("Rp 10 miliar") == ""
    assert preprocess_text("meter") == ""
    assert preprocess_text("ton") == ""
    assert preprocess_text("ribuan ton emas") == "emas"
    assert preprocess_text("ratusan ton") == ""
    assert preprocess_text("belasan ton") == ""
    assert preprocess_text("emas") == "emas"
    assert preprocess_text("tambang") == "tambang"


def test_single_letters_and_fragments_are_removed():
    assert preprocess_text("a x d") == ""
    assert preprocess_text("an ny ber se") == ""
    assert preprocess_text("tjtjkjnmp") == ""


def test_added_dictionary_entries_are_explicit():
    assert preprocess_text("rakyst papua") == "rakyat papua"
    assert preprocess_text("kluar dari freeport") == "keluar freeport"
    assert preprocess_text("donk") == ""
    assert preprocess_text("emasny") == "emas"
    assert preprocess_text("ngola") == "olah"
    assert preprocess_text("harapn") == "harap"
    assert preprocess_text("frepot") == "freeport"
    assert preprocess_text("dn org udah pake bnyak thn") == "orang pakai banyak tahun"
    assert preprocess_text("hnya kpd org") == "hanya orang"
    assert preprocess_text("sj spy lbh baik") == "lebih baik"
    assert preprocess_text("freepot friport pripot mcmoran") == "freeport freeport freeport freeport"
    assert preprocess_text("gressberg gresberg") == "grasberg grasberg"
    assert preprocess_text("suharto sukarno") == "soeharto soekarno"
    assert preprocess_text("america usa china") == "amerika amerika cina"
    assert preprocess_text("jokawi indonesa freport jngan") == "jokowi indonesia freeport jangan"
    assert preprocess_text("mrk trs samapi") == "terus"
    assert preprocess_text("good amazing love") == "bagus hebat suka"
    assert preprocess_text("ijin komen cevron singapore") == "izin komentar chevron singapura"
    assert preprocess_text("nambang ngomong gausah") == "tambang bicara tidak"
    assert preprocess_text("as you my we they up") == ""


def test_unicode_lookalikes_are_normalized():
    assert preprocess_text("nama\u02d0 semo\u0261a") == "nama moga"
    assert preprocess_text("\U0001d635\U0001d622\U0001d62e\U0001d623\U0001d622\U0001d62f\U0001d628") == "tambang"
    assert preprocess_text("lai") == "lain"


def test_repeated_letters_are_normalized_without_harming_double_letters():
    assert preprocess_text("baguuuus") == "bagus"
    assert preprocess_text("bangeeet") == "banget"
    assert preprocess_text("maaf") == "maaf"


def test_dictionary_cache_refreshes_when_file_changes(tmp_path, monkeypatch):
    path = tmp_path / "normalization_id.tsv"
    path.write_text("foo\tbar\n", encoding="utf-8")
    monkeypatch.setattr(normalization, "DICTIONARY_PATH", path)
    normalization.reload_normalization()
    assert normalization.normalize_token("foo") == "bar"
    first_version = preprocessing_version()

    path.write_text("foo\tbaz\n", encoding="utf-8")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert normalization.normalize_token("foo") == "baz"
    assert preprocessing_version() != first_version
    normalization.reload_normalization()
