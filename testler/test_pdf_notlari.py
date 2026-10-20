"""Notlu PDF testleri (K26). Çalıştırma: python -m unittest -v"""

import tempfile
import unittest
from pathlib import Path

import pymupdf

from derskitabi.model import Tespit
from derskitabi.pdf_cikarma import bloklari_cikar
from derskitabi.pdf_notlari import YAZAR, etiket_kutusu, guven_metni, karsi_cumle, notlari_ekle, notlu_pdf_olustur
from testler.test_pdf_cikarma import FONT

S1 = "Cumhuriyet 1923 yılında ilan edildi. Bu bir denme cümlesidir ve okunur."
S2 = "Cumhuriyet 1920 yılında ilan edildi ve herkes sevindi."


def _yaz(sayfa, y, metin):
    sayfa.insert_text((72, y), metin, fontsize=11, fontname="arial", fontfile=str(FONT))


def ornek(yol):
    belge = pymupdf.open()
    _yaz(belge.new_page(), 100, S1)
    _yaz(belge.new_page(), 200, S2)
    belge.set_toc([[1, "Ünite 1", 1]])
    belge.save(yol)


def _tespit(kriter, blok, guven=1.0, **ek):
    return Tespit(blok.sayfa_no, blok.blok_no, blok.bbox, kriter, ek.pop("aciklama", "açıklama"), guven,
                  basili_sayfa_no=None, **ek)


@unittest.skipUnless(FONT.exists(), "Arial fontu bulunamadı")
class NotluPdfTesti(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.TemporaryDirectory()
        self.pdf = Path(self.klasor.name) / "ornek.pdf"
        ornek(self.pdf)
        self.bloklar = bloklari_cikar(self.pdf)
        self.b1, self.b2 = self.bloklar
        self.belge = pymupdf.open(self.pdf)

    def tearDown(self):
        self.belge.close()
        self.klasor.cleanup()

    def notlar(self, sayfa_no, tur=None, belge=None):
        """Notların bilgileri düz veri olarak (PyMuPDF not nesnesi belge kapandıktan sonra
        bellekte kalırsa Python çöküyor)."""
        belge = belge or self.belge
        return [{"tur": a.type[1], "bilgi": dict(a.info), "kutu": pymupdf.Rect(a.rect), "renk": a.colors["stroke"]}
                for a in belge[sayfa_no - 1].annots() if tur in (None, a.type[1])]

    def turler(self, sayfa_no):
        return [n["tur"] for n in self.notlar(sayfa_no)]

    def test_yazim_kelimenin_altina_dalgali_cizgi(self):
        t = _tespit("yazim", self.b1, alt_tur="morfoloji", metin_parcasi="denme")
        sonuc = notlari_ekle(self.belge, self.bloklar, {"yazim": [t], "okunabilirlik": [], "tutarlilik": []})
        self.assertEqual(sonuc["yazim"], 1)
        cizgi = self.notlar(1, "Squiggly")
        self.assertEqual(len(cizgi), 1)
        kelime = self.belge[0].search_for("denme")[0]
        self.assertTrue(cizgi[0]["kutu"].intersects(kelime))
        self.assertEqual(cizgi[0]["bilgi"]["title"], YAZAR)
        self.assertIn("Güven: yüksek", cizgi[0]["bilgi"]["content"])

    def test_dusuk_guven_varsayilan_eklenmez_istenirse_gri(self):
        t = _tespit("yazim", self.b1, 0.25, alt_tur="morfoloji", metin_parcasi="denme")
        sonuc = notlari_ekle(self.belge, self.bloklar, {"yazim": [t]})
        self.assertEqual((sonuc["yazim"], sonuc["dusuk_atlanan"]), (0, 1))
        self.assertEqual(self.turler(1), ["Text"])  # yalnız özet notu
        with pymupdf.open(self.pdf) as belge2:
            notlari_ekle(belge2, self.bloklar, {"yazim": [t]}, dusuk_guven=True)
            renk = self.notlar(1, "Squiggly", belge2)[0]["renk"]
        self.assertEqual([round(v, 2) for v in renk], [0.6, 0.6, 0.6])

    def test_kelime_bulunamazsa_blok_cercevelenir(self):
        t = _tespit("yazim", self.b1, alt_tur="morfoloji", metin_parcasi="xyzq")
        notlari_ekle(self.belge, self.bloklar, {"yazim": [t]})
        self.assertIn("Square", self.turler(1))

    def test_okunabilirlik_paragraf_cercevesi(self):
        t = _tespit("okunabilirlik", self.b1, metin_parcasi=S1, aciklama="en zor %10")
        notlari_ekle(self.belge, self.bloklar, {"okunabilirlik": [t]})
        kare = self.notlar(1, "Square")[0]
        self.assertTrue(kare["kutu"].contains(pymupdf.Rect(self.b1.bbox)))
        self.assertIn("sınıf düzeyini göstermez", kare["bilgi"]["content"])

    def test_tutarlilik_iki_cumle_vurgulanir_ve_birbirine_baglanir(self):
        a = "Cumhuriyet 1923 yılında ilan edildi."
        t = _tespit("tutarlilik", self.b1, alt_tur="kitap_ici_celiski", metin_parcasi=a,
                    ilgili_konumlar=[(2, self.b2.blok_no)])
        kayit = [{"a": {"metin": a, "sayfa_no": 1, "blok_no": self.b1.blok_no},
                  "b": {"metin": S2, "sayfa_no": 2, "blok_no": self.b2.blok_no}, "guven": 1.0}]
        self.assertEqual(karsi_cumle(t, kayit), S2)
        notlari_ekle(self.belge, self.bloklar, {"tutarlilik": [t]}, kayit)
        for no, hedef in ((1, 1), (2, 0)):  # her sayfada vurgu + etiket + karşı sayfaya bağlantı
            turler = self.turler(no)
            self.assertIn("Highlight", turler)
            self.assertIn("FreeText", turler)
            self.assertEqual([l["page"] for l in self.belge[no - 1].get_links()], [hedef])
        vurgu = self.notlar(1, "Highlight")[0]
        self.assertFalse(vurgu["kutu"].intersects(self.belge[0].search_for("denme")[0]))  # yalnız çelişen cümle
        self.assertIn(a, self.notlar(2, "Highlight")[0]["bilgi"]["content"])
        self.assertEqual(self.notlar(1, "FreeText")[0]["bilgi"]["content"], "↔ s. 2")  # görünen yazı

    def test_ozet_notu_ve_yer_imleri(self):
        t = _tespit("yazim", self.b1, alt_tur="morfoloji", metin_parcasi="denme")
        notlari_ekle(self.belge, self.bloklar, {"yazim": [t], "okunabilirlik": [], "tutarlilik": None})
        ozet = self.notlar(1, "Text")[0]["bilgi"]["content"]
        self.assertIn("Yazım ve dil: 1 not", ozet)
        self.assertIn("Bilgi tutarsızlığı: çalıştırılmadı", ozet)
        toc = self.belge.get_toc()
        self.assertEqual(toc[0], [1, "Ünite 1", 1])  # kitabın kendi yer imi korunur
        basliklar = [e[1] for e in toc]
        self.assertIn("İnceleme notları (1)", basliklar)
        self.assertIn("s. 1: denme", basliklar)
        self.assertIn("Dilsel karmaşıklık (okunabilirlik) (bulunmadı)", basliklar)

    def test_dosya_olusturma_sayfalar_ve_metin_degismez(self):
        cikti = Path(self.klasor.name) / "ornek_notlu.pdf"
        t = _tespit("yazim", self.b1, alt_tur="morfoloji", metin_parcasi="denme")
        notlu_pdf_olustur(self.pdf, cikti, bloklar=self.bloklar, yazim_tespitleri=[t], okunabilirlik_tespitleri=[])
        with pymupdf.open(cikti) as yeni:
            self.assertEqual(len(yeni), 2)
            self.assertEqual([p.get_text() for p in yeni], [p.get_text() for p in self.belge])

    def test_etiket_metnin_disinda_genis_kenarda(self):
        sag = etiket_kutusu(595, (68, 100, 540, 200), 120)  # sağda 55, solda 68 boşluk -> sol
        self.assertLessEqual(sag.x1, 68)
        sol = etiket_kutusu(595, (40, 100, 400, 200), 120)
        self.assertGreaterEqual(sol.x0, 400)
        dar = etiket_kutusu(595, (10, 100, 590, 200), 120)  # boşluk yok: sayfanın içinde kalır
        self.assertLessEqual(dar.x1, 595)

    def test_etiket_yazinin_ve_onceki_etiketin_ustune_binmez(self):
        # Sol kenarda yan kutu yazısı var (Biyoloji 10 s.60'ta görüldü): etiket sağa geçer
        yan_kutu = pymupdf.Rect(30, 115, 160, 130)
        r = etiket_kutusu(595, (175, 100, 550, 200), 120, [yan_kutu])
        self.assertFalse(r.intersects(yan_kutu))
        self.assertGreaterEqual(r.x0, 550)
        # Aynı satırdan ikinci etiket: birincinin üstüne binmez
        r2 = etiket_kutusu(595, (175, 100, 550, 200), 120, [yan_kutu, r])
        self.assertFalse(r2.intersects(r) or r2.intersects(yan_kutu))

    def test_guven_metni(self):
        self.assertEqual(guven_metni(1.0), "yüksek (1,0)")
        self.assertEqual(guven_metni(0.5), "orta (0,5)")
        self.assertEqual(guven_metni(0.25), "düşük (0,25)")


if __name__ == "__main__":
    unittest.main()
