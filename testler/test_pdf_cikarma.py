"""PDF çıkarma modülü testleri.

İçeriğini bildiğimiz küçük bir PDF'i test sırasında üretip, modülün doğru
bloklar çıkardığını kontrol eder. Çalıştırma: python -m unittest -v
"""

import tempfile
import unittest
from pathlib import Path

import pymupdf

from derskitabi.kayit import bloklari_kaydet, bloklari_yukle
from derskitabi.pdf_cikarma import MetinYokHatasi, _metni_temizle, bloklari_cikar

# Türkçe karakterleri (ş, ğ, ı, İ) basabilmek için Windows'un Arial fontu kullanılır.
FONT = Path(r"C:\Windows\Fonts\arial.ttf")


def _yaz(sayfa, y, metin):
    sayfa.insert_text((72, y), metin, fontsize=11, fontname="arial", fontfile=str(FONT))


def ornek_pdf(yol, sayfa_etiketi=False):
    """3 sayfalık örnek kitap: kapak + altbilgide numarası olan 2 içerik sayfası."""
    belge = pymupdf.open()

    kapak = belge.new_page()  # A4: 595 x 842 pt
    _yaz(kapak, 300, "TÜRKÇE 6")

    s2 = belge.new_page()
    _yaz(s2, 100, "Birinci paragraf: Türkçe ders kitaplarında öğren-\nciler çok okur.")
    _yaz(s2, 300, "İkinci paragraf ayrı bir bloktur.")
    _yaz(s2, 815, "7")  # altbilgideki basılı sayfa numarası

    s3 = belge.new_page()
    _yaz(s3, 100, "Üçüncü sayfanın tek paragrafı.")
    _yaz(s3, 815, "8")

    if sayfa_etiketi:
        # Kapaktan sonraki sayfalar "iv, v, ..." diye etiketlensin (altbilgidekinden farklı)
        belge.set_page_labels([{"startpage": 1, "prefix": "", "style": "r", "firstpagenum": 4}])
    belge.save(yol)
    belge.close()


class MetinTemizlemeTesti(unittest.TestCase):
    def test_yumusak_tire_birlestirilir(self):
        self.assertEqual(_metni_temizle("öğren­\nciler"), "öğrenciler")

    def test_normal_tire_kucuk_harften_once_birlestirilir(self):
        self.assertEqual(_metni_temizle("kitap-\nlarda"), "kitaplarda")

    def test_gercek_tire_korunur(self):
        self.assertEqual(_metni_temizle("Türk-\nYunan savaşı"), "Türk-Yunan savaşı")
        self.assertEqual(_metni_temizle("1923-\n1938 yılları"), "1923-1938 yılları")

    def test_satir_sonlari_ve_fazla_bosluk_teke_iner(self):
        self.assertEqual(_metni_temizle("Bir\nparagraf  burada.\n"), "Bir paragraf burada.")


@unittest.skipUnless(FONT.exists(), "Arial fontu bulunamadı")
class PdfCikarmaTesti(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.TemporaryDirectory()
        self.pdf = Path(self.klasor.name) / "ornek.pdf"

    def tearDown(self):
        self.klasor.cleanup()

    def test_bloklar_sayfa_ve_sira_numarasiyla_cikar(self):
        ornek_pdf(self.pdf)
        bloklar = bloklari_cikar(self.pdf)
        konumlar = [(b.sayfa_no, b.blok_no) for b in bloklar]
        self.assertEqual(konumlar, [(1, 1), (2, 1), (2, 2), (3, 1)])

    def test_satir_sonu_tiresi_birlestirilir(self):
        ornek_pdf(self.pdf)
        ilk_paragraf = bloklari_cikar(self.pdf)[1]
        self.assertEqual(
            ilk_paragraf.metin, "Birinci paragraf: Türkçe ders kitaplarında öğrenciler çok okur."
        )

    def test_altbilgideki_sayfa_numarasi_okunur_ve_blok_sayilmaz(self):
        ornek_pdf(self.pdf)
        bloklar = bloklari_cikar(self.pdf)
        basili = {b.sayfa_no: b.basili_sayfa_no for b in bloklar}
        self.assertEqual(basili, {1: None, 2: "7", 3: "8"})
        self.assertNotIn("7", [b.metin for b in bloklar])

    def test_sayfa_etiketi_varsa_once_o_kullanilir(self):
        ornek_pdf(self.pdf, sayfa_etiketi=True)
        basili = {b.sayfa_no: b.basili_sayfa_no for b in bloklari_cikar(self.pdf)}
        self.assertEqual(basili[2], "iv")
        self.assertEqual(basili[3], "v")

    def test_bbox_sayfa_icinde_ve_dogru_yerde(self):
        ornek_pdf(self.pdf)
        ikinci = bloklari_cikar(self.pdf)[2]  # y=300'e yazılan paragraf
        x0, y0, x1, y1 = ikinci.bbox
        self.assertTrue(0 <= x0 < x1 <= 595 and 0 <= y0 < y1 <= 842)
        self.assertLess(y0, 300)
        self.assertGreater(y1, 295)

    def test_metinsiz_pdf_anlasilir_hata_verir(self):
        belge = pymupdf.open()
        belge.new_page()
        belge.save(self.pdf)
        belge.close()
        with self.assertRaises(MetinYokHatasi):
            bloklari_cikar(self.pdf)

    def test_json_kaydet_yukle_ayni_bloklari_verir(self):
        ornek_pdf(self.pdf)
        bloklar = bloklari_cikar(self.pdf)
        json_yolu = Path(self.klasor.name) / "bloklar.json"
        bloklari_kaydet(bloklar, json_yolu)
        self.assertEqual(bloklari_yukle(json_yolu), bloklar)


if __name__ == "__main__":
    unittest.main()
