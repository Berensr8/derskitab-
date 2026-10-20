"""Değerlendirme (K20) testleri. Çalıştırma: python -m unittest -v"""

import tempfile
import unittest
from pathlib import Path

from derskitabi.degerlendirme import (KILIT_SHA256, SET_YOLU, celiskileri_uygula, eslesir, ozet, puanla,
                                      set_yukle)
from derskitabi.model import Blok

DEGISTIR = {"id": "X1", "tur": "tarih", "konum": "duz_metin", "yontem": "tekrar_boz",
            "kaynaklar": [{"sayfa_no": 1, "blok_no": 1, "parca": "1071 yılında"}],
            "hedef": {"sayfa_no": 9, "blok_no": 2, "islem": "degistir", "eski": "1071 yılında iki ordu",
                      "yeni": "1074 yılında iki ordu"}}
EKLE = {"id": "X2", "tur": "isim", "konum": "duz_metin", "yontem": "yeniden_yaz",
        "kaynaklar": [{"sayfa_no": 1, "blok_no": 1, "parca": "başkenti Bükreş"}],
        "hedef": {"sayfa_no": 9, "blok_no": 3, "islem": "ekle", "yeni": "Romanya'nın başkenti Köstence şehridir."}}


def bloklar():
    return [Blok(1, 1, (0, 0, 1, 1), "Malazgirt Savaşı 1071 yılında yapıldı. Romanya'nın başkenti Bükreş'tir."),
            Blok(9, 2, (0, 0, 1, 1), "Böylece 1071 yılında iki ordu Malazgirt'te karşılaştı."),
            Blok(9, 3, (0, 0, 1, 1), "Karadeniz kıyısında birçok komşumuz vardır")]


class UygulamaTesti(unittest.TestCase):
    def test_degistir_ve_ekle(self):
        orijinal = bloklar()
        yeni = celiskileri_uygula(orijinal, [DEGISTIR, EKLE])
        self.assertIn("1074 yılında iki ordu", yeni[1].metin)
        self.assertTrue(yeni[2].metin.endswith("vardır. Romanya'nın başkenti Köstence şehridir."))
        self.assertIn("1071 yılında iki ordu", orijinal[1].metin)  # asıl bloklar değişmez

    def test_ifade_bulunamazsa_hata(self):
        bozuk = {**DEGISTIR, "hedef": {**DEGISTIR["hedef"], "eski": "olmayan ifade"}}
        with self.assertRaises(ValueError):
            celiskileri_uygula(bloklar(), [bozuk])


class PuanlamaTesti(unittest.TestCase):
    def test_eslesme_iki_yonde(self):
        a, b = "Malazgirt Savaşı 1071 yılında yapıldı.", "Böylece 1074 yılında iki ordu karşılaştı."
        self.assertTrue(eslesir(DEGISTIR, a, b))
        self.assertTrue(eslesir(DEGISTIR, b, a))
        self.assertFalse(eslesir(DEGISTIR, a, "Başka bir cümle."))

    def test_asamalar_ve_fazladan_tespit(self):
        cumleler = ["Malazgirt Savaşı 1071 yılında yapıldı.", "Böylece 1074 yılında iki ordu karşılaştı.",
                    "Romanya'nın başkenti Bükreş'tir.", "Romanya'nın başkenti Köstence şehridir."]
        kayit = [
            {"a": {"metin": cumleler[0]}, "b": {"metin": cumleler[1]}, "benzerlik": 0.8, "hizli": "celiski", "guven": 1.0},
            {"a": {"metin": cumleler[2]}, "b": {"metin": cumleler[3]}, "benzerlik": 0.9, "hizli": "uyumlu"},
            {"a": {"metin": "Bir cümle."}, "b": {"metin": "Başka cümle."}, "benzerlik": 0.7, "hizli": "celiski", "guven": 0.5},
        ]
        p = puanla([DEGISTIR, EKLE], cumleler, kayit)
        self.assertEqual(p["maddeler"]["X1"]["asama"], "tespit")
        self.assertEqual(p["maddeler"]["X2"]["asama"], "aday")  # aday oldu ama hızlı tur kaçırdı
        self.assertEqual(len(p["fazladan"]), 1)
        o = ozet(p["maddeler"], len(p["fazladan"]))
        self.assertEqual((o["recall"], o["precision"]), (0.5, 0.5))
        self.assertEqual(o["asamaya_ulasan"], {"cumle": 2, "aday": 2, "hizli": 1, "tespit": 1})


class KilitTesti(unittest.TestCase):
    def test_test_seti_kilitlendigi_gibi(self):
        ogeler = set_yukle()
        self.assertEqual(len(ogeler), 50)
        self.assertEqual(sum(o["set"] == "gelistirme" for o in ogeler), 15)

    def test_degisen_set_reddedilir(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "set.json"
            yol.write_bytes(SET_YOLU.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                set_yukle(yol, KILIT_SHA256)


if __name__ == "__main__":
    unittest.main()
