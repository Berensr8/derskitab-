"""Etkileşimli inceleyici testleri. Çalıştırma: python -m unittest -v"""

import json
import re
import tempfile
import unittest
from pathlib import Path

import pymupdf

from derskitabi.gorsellestir import blok_raporu
from derskitabi.inceleyici import inceleme_html_olustur, satirlari_birlestir
from derskitabi.model import Blok
from testler.test_pdf_cikarma import FONT, ornek_pdf


class SatirBirlestirmeTesti(unittest.TestCase):
    def test_ayni_satirdaki_kelimeler_tek_kutu(self):
        kutular = [pymupdf.Rect(10, 100, 30, 110), pymupdf.Rect(35, 100, 60, 110)]
        self.assertEqual(satirlari_birlestir(kutular), [[10, 100, 60, 110]])

    def test_farkli_satirlar_ayri_kalir(self):
        kutular = [pymupdf.Rect(10, 100, 30, 110), pymupdf.Rect(10, 115, 40, 125)]
        self.assertEqual(len(satirlari_birlestir(kutular)), 2)


class HesapAdimlariTesti(unittest.TestCase):
    def test_ara_degerler_elle_hesapla_ayni(self):
        # FormulTesti ile aynı örnek: 2 cümle, 6 kelime, 13 hece, H3 = 1/2
        b = Blok(1, 1, (0, 0, 1, 1), "Ali okula gitti. Ayşe eve geldi.", "1", "paragraf")
        h = blok_raporu(b)["skorlar"]["hesap"]
        self.assertEqual((h["cumle"], h["kelime"], h["hece"]), (2, 6, 13))
        self.assertAlmostEqual(h["kelime_cumle"], 3.0)
        self.assertEqual(h["h"], {"3": 0.5, "4": 0.0, "5": 0.0, "6": 0.0})


@unittest.skipUnless(FONT.exists(), "Arial fontu bulunamadı")
class InceleyiciHtmlTesti(unittest.TestCase):
    def test_html_veriyi_ve_secilen_sayfalari_icerir(self):
        with tempfile.TemporaryDirectory() as klasor:
            pdf = Path(klasor) / "ornek.pdf"
            cikti = Path(klasor) / "inceleme.html"
            ornek_pdf(pdf)
            inceleme_html_olustur(pdf, cikti, sayfalar=[2, 3])
            html = cikti.read_text(encoding="utf-8")
        self.assertNotIn("/*__VERI__*/", html)  # şablondaki yer tutucu doldurulmuş
        veri = json.loads(re.search(r"const VERI = (.*);\n", html).group(1))
        self.assertEqual([s["no"] for s in veri["sayfalar"]], [2, 3])
        ilk = veri["sayfalar"][0]["bloklar"][0]
        self.assertTrue(ilk["rapor"]["metin"].startswith("Birinci paragraf"))
        self.assertEqual(len(ilk["cumle_kutulari"]), 1)  # tek cümle, vurgu kutusu bulundu
        self.assertTrue(veri["sayfalar"][0]["goruntu"].startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()
