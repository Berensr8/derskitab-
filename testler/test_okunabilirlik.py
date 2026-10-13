"""Okunabilirlik kriteri testleri. Çalıştırma: python -m unittest -v"""

import unittest

from derskitabi.kriterler.okunabilirlik import (
    analiz_et, atesman_duzeyi, bezirci_yilmaz_duzeyi, cetinkaya_uzun_duzeyi, cumlelere_bol,
    hece_sayisi, hedef_sinifi_bul, kelimeler, skorla,
)
from derskitabi.model import Blok


def blok(metin, sayfa=10, no=1, tur="paragraf"):
    return Blok(sayfa, no, (0.0, 0.0, 100.0, 20.0), metin, str(sayfa), tur)


class HeceVeKelimeTesti(unittest.TestCase):
    def test_hece_sayisi_unlu_sayisidir(self):
        self.assertEqual(hece_sayisi("kitap"), 2)
        self.assertEqual(hece_sayisi("öğrenciler"), 4)
        self.assertEqual(hece_sayisi("Atatürk’ün"), 4)
        self.assertEqual(hece_sayisi("tren"), 1)

    def test_rakamlar_kelime_sayilmaz(self):
        self.assertEqual(kelimeler("1919 yılında 19 Mayıs"), ["yılında", "Mayıs"])

    def test_kesme_isaretli_kelime_tek_kelimedir(self):
        self.assertEqual(kelimeler("Atatürk’ün sözü"), ["Atatürk’ün", "sözü"])


class CumleBolmeTesti(unittest.TestCase):
    def test_noktalama_ile_bolunur(self):
        self.assertEqual(len(cumlelere_bol("Ali okula gitti. Ayşe de geldi.")), 2)
        self.assertEqual(len(cumlelere_bol("Ne dersin? Gel!")), 2)

    def test_kisaltmalar_bolmez(self):
        self.assertEqual(len(cumlelere_bol("M.Ö. 3000 yılında yazı bulundu. Bu önemlidir.")), 2)
        self.assertEqual(len(cumlelere_bol("Kitap, defter vb. Araçlar gerekir.")), 1)

    def test_sira_sayisi_ve_ondalik_bolmez(self):
        self.assertEqual(len(cumlelere_bol("6. sınıf öğrencileri geldi.")), 1)
        self.assertEqual(len(cumlelere_bol("Görsel 1.31'e bakınız.")), 1)

    def test_bosluksuz_cumle_sonu_bolunur(self):
        # Gerçek kitaptan: s.31 (Kaynak 5) ve s.15
        self.assertEqual(len(cumlelere_bol("Sanat hâline gelmiştir.(…) En sık desen çiçektir.")), 2)
        self.assertEqual(len(cumlelere_bol("Roller alabiliriz.Öğrenci rolüyle bilgi ediniriz.")), 2)

    def test_bosluksuz_kisaltmalar_bolunmez(self):
        self.assertEqual(len(cumlelere_bol("T.B.M.M. 1920'de açıldı.")), 1)
        self.assertEqual(len(cumlelere_bol("Kaynak: s.230 ve Dr.Ahmet'in notları.")), 1)

    def test_tirnakli_cumle_sonu(self):
        self.assertEqual(len(cumlelere_bol('"Yurtta sulh, cihanda sulh." Bu sözü biliriz.')), 2)


class FormulTesti(unittest.TestCase):
    def test_formuller_elle_hesaplanan_degerleri_verir(self):
        # "Ali okula gitti. Ayşe eve geldi."
        # 2 cümle, 6 kelime; heceler: Ali 2, okula 3, gitti 2, Ayşe 2, eve 2, geldi 2 = 13
        # hece/kelime = 13/6 = 2,1667   kelime/cümle = 6/2 = 3
        # Ateşman        = 198,825 - 40,175 x 2,1667 - 2,610 x 3 = 103,95
        # Çetinkaya-Uzun = 118,823 - 25,987 x 2,1667 - 0,971 x 3 = 59,60
        # Bezirci-Yılmaz: H3 = 1 (okula) / 2 cümle = 0,5 -> karekök(3 x 0,5 x 0,84) = 1,12
        s = skorla("Ali okula gitti. Ayşe eve geldi.")
        self.assertEqual((s.cumle_sayisi, s.kelime_sayisi), (2, 6))
        self.assertAlmostEqual(s.atesman, 103.95, places=2)
        self.assertAlmostEqual(s.cetinkaya_uzun, 59.60, places=2)
        self.assertAlmostEqual(s.bezirci_yilmaz, 1.12, places=2)

    def test_alti_ve_daha_fazla_heceli_kelimeler_h6_sayilir(self):
        # "Anlaşılabilirlik" 7 hece -> H6 = 1; karekök(1 x 1 x 26,25) = 5,12
        self.assertAlmostEqual(skorla("Anlaşılabilirlik.").bezirci_yilmaz, 5.12, places=2)

    def test_kelimesiz_metin_skorlanmaz(self):
        self.assertIsNone(skorla("1919 - 1923"))


class DuzeyTablosuTesti(unittest.TestCase):
    def test_atesman_sinirlari(self):
        self.assertEqual(atesman_duzeyi(90), "çok kolay")
        self.assertEqual(atesman_duzeyi(89.9), "kolay")
        self.assertEqual(atesman_duzeyi(50), "orta güçlükte")
        self.assertEqual(atesman_duzeyi(49.9), "zor")
        self.assertEqual(atesman_duzeyi(29.9), "çok zor")

    def test_cetinkaya_uzun_sinirlari(self):
        self.assertIn("5–7", cetinkaya_uzun_duzeyi(51))
        self.assertIn("8–9", cetinkaya_uzun_duzeyi(35))
        self.assertIn("10–12", cetinkaya_uzun_duzeyi(34.9))

    def test_bezirci_yilmaz_sinirlari(self):
        self.assertIn("ilköğretim", bezirci_yilmaz_duzeyi(8))
        self.assertIn("lise", bezirci_yilmaz_duzeyi(12))
        self.assertEqual(bezirci_yilmaz_duzeyi(12.1), "lisans")
        self.assertEqual(bezirci_yilmaz_duzeyi(16.1), "akademik")


class HedefSinifTesti(unittest.TestCase):
    def test_kapaktan_bulunur(self):
        self.assertEqual(hedef_sinifi_bul([blok("SOSYAL BİLGİLER", 1), blok("6 SINIF", 1, 2)]), 6)
        self.assertEqual(hedef_sinifi_bul([blok("Türkçe 5. Sınıf Ders Kitabı", 2)]), 5)

    def test_bulunamazsa_none(self):
        self.assertIsNone(hedef_sinifi_bul([blok("SOSYAL BİLGİLER", 1)]))

    def test_kapak_sonrasindaki_sayfalara_bakilmaz(self):
        self.assertIsNone(hedef_sinifi_bul([blok("8. sınıfta göreceğiz", 40)]))


KOLAY = "Ali eve geldi. Ayşe okula gitti. Hava çok güzeldi."
ZOR = (
    "Gelenek ve görenekler günlük yaşamımızda insanların tutum ve davranışlarını "
    "düzenlemede, toplumsal ilişkileri kolaylaştırmada, birlik ve beraberliği "
    "güçlendirmede önemli sorumluluklar üstlenmektedir. Uluslararası kuruluşlarla "
    "gerçekleştirilen işbirlikleri sürdürülebilir kalkınmayı desteklemektedir. "
    "Anlaşılabilirlik değerlendirmeleri sistematikleştirilmiştir."
)


class AnalizTesti(unittest.TestCase):
    def kitap(self):
        bloklar = [blok("6 SINIF", 1, 1, "kisa")]
        bloklar += [blok(KOLAY, 10 + i) for i in range(9)]
        bloklar.append(blok(ZOR, 30, 4))
        bloklar.append(blok("Kısa tek cümlelik bir paragraf burada.", 31))
        bloklar.append(blok("Edirne Kırklareli", 31, 2, "kisa"))
        return bloklar

    def test_yalnizca_belirgin_zor_paragraf_isaretlenir(self):
        ozet, tespitler = analiz_et(self.kitap())
        self.assertEqual(len(tespitler), 1)
        t = tespitler[0]
        self.assertEqual((t.sayfa_no, t.blok_no, t.kriter), (30, 4, "okunabilirlik"))
        self.assertEqual(t.guven_skoru, 1.0)  # 3 formül de hemfikir
        self.assertTrue(t.metin_parcasi.startswith("Gelenek"))  # en uzun cümle

    def test_ozet_hedef_sinif_ve_sayilar(self):
        ozet, _ = analiz_et(self.kitap())
        self.assertEqual(ozet.hedef_sinif, 6)
        self.assertEqual(ozet.paragraf_sayisi, 11)  # "kisa" türündekiler katılmaz
        self.assertEqual(ozet.degerlendirilen_paragraf, 10)  # tek cümlelik aday değil

    def test_elle_verilen_sinif_kapagi_ezer(self):
        ozet, _ = analiz_et(self.kitap(), hedef_sinif=7)
        self.assertEqual(ozet.hedef_sinif, 7)

    def test_az_paragrafta_yalnizca_ozet_verilir(self):
        ozet, tespitler = analiz_et([blok(KOLAY), blok(ZOR, 11)])
        self.assertEqual(tespitler, [])
        self.assertEqual(ozet.paragraf_sayisi, 2)


if __name__ == "__main__":
    unittest.main()
