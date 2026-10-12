"""Görselleştirme aracı testleri. Çalıştırma: python -m unittest -v"""

import tempfile
import unittest
from pathlib import Path

import pymupdf

from derskitabi.gorsellestir import (
    blok_raporu, isaretli_pdf_olustur, kelimeleri_eslestir, rapor_metni, sayfa_araligi_coz,
)
from derskitabi.model import Blok
from testler.test_pdf_cikarma import FONT, ornek_pdf


class KelimeEslestirmeTesti(unittest.TestCase):
    def test_birebir_eslesme(self):
        self.assertEqual(kelimeleri_eslestir(["Ali", "geldi."], ["Ali", "geldi."]), [[0], [1]])

    def test_yumusak_tireyle_bolunmus_kelime_iki_parcadan_gelir(self):
        ham = ["Türkçe", "öğren­", "ciler"]
        self.assertEqual(kelimeleri_eslestir(ham, ["Türkçe", "öğrenciler"]), [[0], [1, 2]])

    def test_normal_tireyle_bolunmus_kelime(self):
        self.assertEqual(kelimeleri_eslestir(["kitap-", "larda"], ["kitaplarda"]), [[0, 1]])

    def test_gercek_tire_korunur(self):
        self.assertEqual(kelimeleri_eslestir(["Türk-", "Yunan"], ["Türk-Yunan"]), [[0, 1]])

    def test_eslesmezse_none(self):
        self.assertIsNone(kelimeleri_eslestir(["Ali", "geldi"], ["Veli", "geldi"]))
        self.assertIsNone(kelimeleri_eslestir(["Ali"], ["Ali", "geldi"]))


class SayfaAraligiTesti(unittest.TestCase):
    def test_aralik_ve_tek_sayfa(self):
        self.assertEqual(sayfa_araligi_coz("2-4,9", 10), [2, 3, 4, 9])

    def test_tekrarlar_birlesir(self):
        self.assertEqual(sayfa_araligi_coz("3,1-3", 10), [1, 2, 3])

    def test_gecersiz(self):
        with self.assertRaises(ValueError):
            sayfa_araligi_coz("abc", 10)
        with self.assertRaises(ValueError):
            sayfa_araligi_coz("9-12", 10)


class BlokRaporuTesti(unittest.TestCase):
    def test_paragraf_cumle_hece_ve_skor_icerir(self):
        b = Blok(1, 3, (0, 0, 1, 1), "Ali okula gitti. Ayşe eve geldi.", "1", "paragraf")
        r = blok_raporu(b)
        self.assertEqual(len(r["cumleler"]), 2)
        self.assertEqual(r["cumleler"][0]["kelimeler"], [("Ali", 2), ("okula", 3), ("gitti", 2)])
        self.assertFalse(r["skorlar"]["tespit_adayi"])  # 3 cümleden az
        metin = rapor_metni(r)
        self.assertIn("2 cümle · 6 kelime · 13 hece", metin)
        self.assertIn("okula(3)", metin)

    def test_bozuk_blok_skorlanmaz(self):
        r = blok_raporu(Blok(1, 1, (0, 0, 1, 1), "Bast��n", None, "bozuk"))
        self.assertIsNone(r["skorlar"])
        self.assertIn("okunamıyor", r["tur_aciklamasi"])


@unittest.skipUnless(FONT.exists(), "Arial fontu bulunamadı")
class IsaretliPdfTesti(unittest.TestCase):
    def test_secilen_sayfalar_ve_her_blok_icin_not(self):
        with tempfile.TemporaryDirectory() as klasor:
            pdf = Path(klasor) / "ornek.pdf"
            cikti = Path(klasor) / "isaretli.pdf"
            ornek_pdf(pdf)
            isaretli_pdf_olustur(pdf, cikti, sayfalar=[2])
            with pymupdf.open(cikti) as belge:
                self.assertEqual(len(belge), 1)  # yalnızca seçilen sayfa
                basliklar = [a.info["title"] for a in belge[0].annots()]
        self.assertEqual(basliklar, ["Blok 1 (paragraf)", "Blok 2 (paragraf)"])


if __name__ == "__main__":
    unittest.main()
