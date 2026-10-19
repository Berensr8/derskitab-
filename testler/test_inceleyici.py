"""Etkileşimli inceleyici testleri. Çalıştırma: python -m unittest -v"""

import json
import re
import tempfile
import unittest
from pathlib import Path

import pymupdf

from derskitabi.gorsellestir import blok_raporu
from derskitabi.inceleyici import inceleme_html_olustur, parca_kutulari, satirlari_birlestir, yazim_izi
from derskitabi.kriterler import yazim
from derskitabi.model import Blok
from testler.test_pdf_cikarma import FONT, ornek_pdf


class SatirBirlestirmeTesti(unittest.TestCase):
    def test_ayni_satirdaki_kelimeler_tek_kutu(self):
        kutular = [pymupdf.Rect(10, 100, 30, 110), pymupdf.Rect(35, 100, 60, 110)]
        self.assertEqual(satirlari_birlestir(kutular), [[10, 100, 60, 110]])

    def test_farkli_satirlar_ayri_kalir(self):
        kutular = [pymupdf.Rect(10, 100, 30, 110), pymupdf.Rect(10, 115, 40, 125)]
        self.assertEqual(len(satirlari_birlestir(kutular)), 2)


class ParcaKutusuTesti(unittest.TestCase):
    HAM = [(pymupdf.Rect(0, 0, 30, 10), "ikiye"), (pymupdf.Rect(35, 0, 90, 10), "katlandı.Takım"),
           (pymupdf.Rect(95, 0, 140, 10), "arkadaşlarımla"), (pymupdf.Rect(0, 20, 40, 30), "kisisel")]

    def test_kelime_tespiti_tek_kutu(self):
        self.assertEqual(parca_kutulari(self.HAM, "kisisel"), [[0, 20, 40, 30]])

    def test_noktalama_tespitinde_noktalamali_kelime_isaretlenir(self):
        # Kural tespitinin parçası bir kesittir: "iye katlandı.Takım arkada"
        self.assertEqual(parca_kutulari(self.HAM, "iye katlandı.Takım arkada"), [[35, 0, 90, 10]])


class HesapAdimlariTesti(unittest.TestCase):
    def test_ara_degerler_elle_hesapla_ayni(self):
        # FormulTesti ile aynı örnek: 2 cümle, 6 kelime, 13 hece, H3 = 1/2
        b = Blok(1, 1, (0, 0, 1, 1), "Ali okula gitti. Ayşe eve geldi.", "1", "paragraf")
        h = blok_raporu(b)["skorlar"]["hesap"]
        self.assertEqual((h["cumle"], h["kelime"], h["hece"]), (2, 6, 13))
        self.assertAlmostEqual(h["kelime_cumle"], 3.0)
        self.assertEqual(h["h"], {"3": 0.5, "4": 0.0, "5": 0.0, "6": 0.0})


class YazimIziTesti(unittest.TestCase):
    """İnceleyicinin "adım adım" gösterdiği kelime durumları, yazım kriterinin gerçek
    kararlarıyla aynı olmalı (sahte denetçilerle, test_yazim.py'deki gibi)."""

    def test_kelime_durumlari(self):
        sozluk = {"ali", "okula", "gitti", "ve", "kitap", "okudu", "sınıfta"}
        denetciler = (lambda k: k in sozluk, lambda k: k in sozluk | {"nesile"})
        b = Blok(10, 1, (0, 0, 100, 20), "Ali okula gitti ve sınıfta kitap okudu ve kisisel nesile "
                 "villus Bakırçay kitap okudu okula gitti.", "10", "paragraf")
        terim_bloklari = [Blok(11, i, (0, 0, 1, 1), "villus villus", "11", "kisa") for i in range(2)]
        kitap = [b] + terim_bloklari
        tespitler = yazim.analiz_et([b], denetciler, kitap_bloklari=kitap)
        baglam = {"denetciler": denetciler, "kitap_kelimeleri": yazim.kitap_kelime_sayilari(kitap)}
        iz = yazim_izi(b, tespitler, baglam, ham=[])
        durum = {k["k"]: k["d"] for k in iz["kelimeler"]}
        self.assertEqual(durum["okula"], "gecerli")
        self.assertEqual(durum["kisisel"], "hata")       # ikisi de tanımadı
        self.assertEqual(durum["nesile"], "supheli")     # yalnız biri tanımadı
        self.assertEqual(durum["villus"], "terim")       # kitapta 5 kez
        self.assertEqual(durum["Bakırçay"], "atlandi")   # büyük harf: özel isim
        self.assertEqual(iz["durum"], "denetlendi")

    def test_okuma_sorunlu_blokta_kelimeler_hata_sayilmaz(self):
        # 8 uzun kelimeden 3'ü (%37) tanınmıyor: eşik %30 aşıldı, blok PDF okuma sorunu
        sozluk = {"okula", "gitti", "kitap", "okudu", "nesile"}
        denetciler = (lambda k: k in sozluk, lambda k: k in sozluk)
        b = Blok(10, 1, (0, 0, 1, 1), "Ali okula gitti kisisel nesile villus Bakırçay kitap okudu", "10")
        baglam = {"denetciler": denetciler, "kitap_kelimeleri": yazim.kitap_kelime_sayilari([b])}
        iz = yazim_izi(b, yazim.analiz_et([b], denetciler), baglam, ham=[])
        self.assertEqual(iz["durum"], "okuma_orani")
        self.assertEqual({k["k"]: k["d"] for k in iz["kelimeler"]}["kisisel"], "okuma")

    def test_bozuk_blok_icin_iz_yok(self):
        b = Blok(1, 1, (0, 0, 1, 1), "Kar��la�t�rma", "1", "bozuk")
        self.assertIsNone(yazim_izi(b, [], {}, ham=[]))


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
        self.assertEqual(ilk["yazim_izi"]["durum"], "denetlendi")  # adım adım yazım verisi var


if __name__ == "__main__":
    unittest.main()
