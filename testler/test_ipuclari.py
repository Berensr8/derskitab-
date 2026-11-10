"""Kitap ipuçları testleri (K29): PDF okuma parçası, terim, birleşik işaretleme.
Çalıştırma: python -m unittest -v"""

import unittest

from derskitabi.kriterler import dusuk_oncelik, pdf_parcasi, terim
from derskitabi.model import Blok, Tespit

GECERLI = {"kıymetli", "dikdörtgen", "eşitlikleri", "daha", "olay", "örgüsüne", "ve", "bir", "hazinendir"}
SAHTE_ARAC = (lambda k: k in GECERLI, lambda k: k in GECERLI)  # iki "araç" da aynı küçük sözlük


def tespit(blok_no, parca, alt_tur="morfoloji", guven=1.0):
    return Tespit(1, blok_no, (0, 0, 1, 1), "yazim", "Açıklama.", guven, alt_tur=alt_tur, metin_parcasi=parca)


def blok(no, metin):
    return Blok(1, no, (0, 0, 1, 1), metin, "1", "paragraf")


class PdfParcasiTesti(unittest.TestCase):
    def test_ozel_glife_bitisik_parca(self):
        sebep, _ = pdf_parcasi.kelime_sebebi("kymetli hazinendir", "ymetli", SAHTE_ARAC)
        self.assertIn("özel bir yazı tipi işareti", sebep)

    def test_rakama_bitisik_ve_sayiya_gelen_ek(self):
        self.assertIn("rakama bitişik", pdf_parcasi.kelime_sebebi("ölçüsü 180cden küçük", "cden", SAHTE_ARAC)[0])
        self.assertIn("sayıya getirilen ek", pdf_parcasi.kelime_sebebi("1960’larda Japonya", "larda", SAHTE_ARAC)[0])

    def test_dusmus_harf_komsuyla_birlesir(self):
        sebep, _ = pdf_parcasi.kelime_sebebi("ABCD dikd rtgen ve", "rtgen", SAHTE_ARAC)
        self.assertIn("dikdörtgen", sebep)

    def test_ayri_yazilmis_kelime_indirilmez_aciklanir(self):
        sebep, ek = pdf_parcasi.kelime_sebebi("verilen eşitlik leri", "leri", SAHTE_ARAC)
        self.assertIsNone(sebep)
        self.assertIn("eşitlikleri", ek)

    def test_gercek_hata_dokunulmaz(self):
        self.assertEqual(pdf_parcasi.kelime_sebebi("bu kisisel bir konu", "kisisel", SAHTE_ARAC), (None, ""))

    def test_blok_sinirinda_bolunmus_kural_tespiti(self):
        bloklar = [blok(1, "olay örgüsüne da"), blok(2, "ha çok önem verdi")]
        sonuc = pdf_parcasi.isaretle([tespit(1, "örgüsüne da", "bag_de_da_uyum")], bloklar, SAHTE_ARAC)
        self.assertEqual(sonuc[0].guven_skoru, pdf_parcasi.DUSUK_GUVEN)
        self.assertIn("daha", sonuc[0].aciklama)


class TerimTesti(unittest.TestCase):
    def test_sozluk_maddeleri(self):
        bloklar = [blok(1, "aken : Alt durumlu ovaryumlarda meydana gelen meyve."),
                   blok(2, "kitâbe (kitabe) : Yazıt."), blok(3, "Bu bir paragraftır: madde değil.")]
        maddeler = terim.sozluk_maddeleri(bloklar)
        self.assertTrue({"aken", "kitâbe"} <= maddeler)
        self.assertNotIn("bu", maddeler)
        self.assertEqual(terim.sozlukte_mi("akenlerin", maddeler), "aken")
        # Ek almış hâl yalnız araçların tanımadığı maddede: bilinen "etme" ile "etmeize" terim olmaz
        self.assertIsNone(terim.sozlukte_mi("etmeize", {"etme"}, bilinen=lambda m: m == "etme"))

    def test_italik_ad_ve_okunusu(self):
        metin = "Diken kelebeği [Vanessa cardui (vanesa karduyi)] türü"
        self.assertEqual(terim.okunus_kelimeleri(metin, {"vanessa", "cardui"}), {"vanesa", "karduyi"})
        bloklar = [blok(1, metin)]
        sonuc = terim.isaretle([tespit(1, "cardui"), tespit(1, "karduyi"), tespit(1, "kelebeği")], bloklar,
                               {(1, 1): {"vanessa", "cardui"}}, SAHTE_ARAC)
        self.assertEqual([t.guven_skoru for t in sonuc], [terim.DUSUK_GUVEN, terim.DUSUK_GUVEN, 1.0])

    def test_coklu_ve_harf_baslikli_sozluk_maddeleri(self):
        b = blok(1, "A-B-C adaptasyon : Bir canlının uyumu. adiponektin : Yağ dokusu hormonu.")
        maddeler = terim.sozluk_maddeleri([b])
        self.assertIn("adaptasyon", maddeler)
        self.assertIn("adiponektin", maddeler)

    def test_tanim_ve_parantez_terimleri(self):
        b1 = blok(1, "Hücrelerin salgıladığı ara maddeye ise kondrin denir.")
        b2 = blok(2, "Zarda proteine bağlı karbohidratlar (glikoprotein) bulunur.")
        b3 = blok(3, "Gözyaşında bulunan lizozim enzimi mikropları öldürür.")
        sonuc = terim.isaretle([tespit(1, "kondrin"), tespit(2, "glikoprotein"), tespit(3, "lizozim")],
                               [b1, b2, b3], None, SAHTE_ARAC)
        for t in sonuc:
            self.assertEqual(t.guven_skoru, terim.DUSUK_GUVEN)
            self.assertIn(terim.TERIM_NOTU, t.aciklama)

    def test_taninan_kokun_hatali_eki_terim_sayilmaz(self):
        # "asit" araçlarca tanınan bir kelimedir; "asiti" (doğrusu: asidi) ve "asitbaz"
        # terim önekiyle gizlenmemelidir (K41-ek).
        b = blok(1, "Hidrofobik kuyruk (yağ asiti) ve asitbaz dengesi.")
        t_asiti = tespit(1, "asiti")
        t_asitbaz = tespit(1, "asitbaz")
        sozluk = {"asit", "hidrofobik", "kuyruk", "dengesi", "ve"}
        sahte = (lambda k: k in sozluk, lambda k: k in sozluk)
        sonuc = terim.isaretle([t_asiti, t_asitbaz], [b], None, sahte)
        self.assertEqual(sonuc[0].guven_skoru, 1.0)
        self.assertEqual(sonuc[1].guven_skoru, 1.0)


class BirlesikTesti(unittest.TestCase):
    def test_ilk_uyan_sebep_ve_kisa_ad(self):
        bloklar = [blok(1, "kymetli hazinendir"), blok(2, "aken : Bir meyve türü."), blok(3, "bu kisisel")]
        t = [tespit(1, "ymetli"), tespit(2, "aken"), tespit(3, "kisisel")]
        sonuc = dusuk_oncelik.isaretle(None, bloklar, t, SAHTE_ARAC)  # PDF'siz: yalnız metin ipuçları
        self.assertEqual([dusuk_oncelik.sebep(x) for x in sonuc], ["PDF okuma parçası", "terim", None])
        self.assertEqual(sonuc[2].guven_skoru, 1.0)

    def test_yalniz_bir_arac_tanimadi_sebebi(self):
        t = Tespit(1, 1, (0, 0, 1, 1), "yazim", "kelime çözümlenemedi (yalnız Starlang); yazım hatası olabilir (yalnız bir araç tanımadı).",
                   0.25, alt_tur="morfoloji", metin_parcasi="test")
        self.assertEqual(dusuk_oncelik.sebep(t), "yalnız bir araç tanımadı")


if __name__ == "__main__":
    unittest.main()
