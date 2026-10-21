"""Alıntı ayırma testleri (K28). Çalıştırma: python -m unittest -v"""

import unittest

from derskitabi.kriterler.alinti import (ALINTI_NOTU, DUSUK_GUVEN, ad_gibi_mi, alinti_bloklari,
                                         alintilari_isaretle, eski_dil_mi, imza_mi, replik_bloklari)
from derskitabi.model import Blok, Tespit

SIIR = "Ah bu türküler köy türküleri Karanlık kuyularda açılmış çiçekler gibi Kiminin reyhasından geçilmez"
METIN = "Şiirde şairin kullandığı takma ada mahlas denir ve halk şiirinde tapşırma olarak bilinir."


def blok(no, bbox, metin, tur="paragraf"):
    return Blok(1, no, bbox, metin, "1", tur)


class AdTesti(unittest.TestCase):
    """Starlang ile; araç kurulu değilse atlanır."""

    @classmethod
    def setUpClass(cls):
        try:
            from derskitabi.kriterler.yazim import starlang_cozumleyici
            starlang_cozumleyici()
        except ImportError as e:
            raise unittest.SkipTest(f"morfoloji araçları kurulu değil: {e}")

    def test_yazar_imzalari(self):
        for imza in ("Hüseyin Nihal Atsız", "Bedri Rahmi Eyüboğlu, Karadut", "Neclâ Pekolcay", "Fuzûlî",
                     "Anonim (haz.: Mutlu Güleryüzlü)", "Karacaoğlan", "Mehmet Kaplan, Şiir Tahlilleri",
                     "Âşık Ali İzzet"):
            self.assertTrue(ad_gibi_mi(imza), imza)

    def test_bilinen_sinirlama_iki_kelimesi_de_siradan_olabilen_ad(self):
        # "Nâzım" sözlükte sıfat, "Hikmet" sıradan isim de: kesin ad yok, imza sayılmıyor (K28)
        self.assertFalse(ad_gibi_mi("Nâzım Hikmet, Bütün Şiirleri"))

    def test_altyazi_baslik_ve_yer_adlari_imza_degil(self):
        for metin in ("Görsel 1.19", "Bilgi Kutusu", "Altay Dağları", "Ergenekon Destanı", "Trabzon",
                      "Analitik Dereceli Puanlama Anahtarı", "Genel ağdan alınmıştır", "ADP"):
            self.assertFalse(ad_gibi_mi(metin), metin)

    def test_imza_konumu_ve_puntosu(self):
        ust = blok(1, (183, 600, 306, 687), SIIR)
        imza = blok(2, (255, 700, 384, 715), "Bedri Rahmi Eyüboğlu, Karadut", "kisa")
        self.assertTrue(imza_mi(imza, ust, [ust], ("Avenir-Roman", 9), ("Avenir-Roman", 10)))
        # Harita etiketi kadar küçük yazı: imza değil
        self.assertFalse(imza_mi(imza, ust, [ust], ("Arial", 3), ("Avenir-Roman", 10)))
        # Metinden büyük punto: imza değil (başlık)
        self.assertFalse(imza_mi(imza, ust, [ust], ("Avenir-Roman", 12), ("Avenir-Roman", 10)))

    def test_ayni_puntoda_imza_yalniz_alintinin_sag_kenarina_uzanirsa(self):
        ust = blok(1, (65, 63, 522, 171), SIIR)
        sagda = blok(2, (466, 175, 522, 192), "Peyami Safa", "kisa")
        ortada = blok(3, (200, 175, 300, 192), "Peyami Safa", "kisa")
        bicim = ("Charter-Roman", 10)
        self.assertTrue(imza_mi(sagda, ust, [ust], bicim, bicim))
        self.assertFalse(imza_mi(ortada, ust, [ust], bicim, bicim))

    def test_siirde_her_dize_ayri_blok_kelimeler_alintinin_tamaminda_sayilir(self):
        dizeler = [blok(i, (65, 100 + 18 * i, 260, 115 + 18 * i), d) for i, d in enumerate(
            ["Şühedâ gövdesi, bir baksana dağlar taşlar...", "O, rükû olmasa, dünyada eğilmez başlar,",
             "Vurulup tertemiz alnından, uzanmış yatıyor,"], start=1)]
        imza = blok(9, (180, 172, 260, 184), "Mehmet Akif Ersoy", "kisa")
        bicim = {(1, i): ("Charter-Roman", 10) for i in range(1, 4)} | {(1, 9): ("Charter-Roman", 9)}
        self.assertEqual(set(alinti_bloklari(dizeler + [imza], bicim)), {(1, 1), (1, 2), (1, 3)})

    def test_imzanin_ustundeki_ayni_bicimli_bloklar_alinti(self):
        bloklar = [blok(1, (60, 100, 500, 130), METIN), blok(2, (183, 150, 384, 300), SIIR),
                   blok(3, (183, 302, 360, 320), "(...)", "kisa"), blok(4, (183, 322, 384, 600), SIIR),
                   blok(5, (255, 605, 384, 618), "Bedri Rahmi Eyüboğlu, Karadut", "kisa")]
        bicim = {(1, 1): ("Baskerville", 10), (1, 2): ("Avenir-Roman", 10), (1, 3): ("Avenir-Book", 10),
                 (1, 4): ("Avenir-Roman", 10), (1, 5): ("Avenir-Roman", 9)}
        al = alinti_bloklari(bloklar, bicim)
        self.assertEqual(set(al), {(1, 2), (1, 4)})  # "(...)" atlanır, farklı biçimli açıklama alıntı değil
        self.assertEqual(al[(1, 2)], "Bedri Rahmi Eyüboğlu, Karadut")

    def test_v3_ayni_puntoda_kalin_yazar_eser_imzasi(self):
        ust = blok(1, (56, 268, 262, 344), SIIR)
        imza = blok(2, (56, 347, 311, 360), "Necip Fazıl Kısakürek, Çile", "kisa")
        normal, kalin = ("MyriadPro-Regular", 10), ("MyriadPro-Semibold", 10)
        self.assertTrue(imza_mi(imza, ust, [ust], kalin, normal))
        # Altında alıntının yazı tipiyle metin devam ediyorsa başlıktır
        self.assertFalse(imza_mi(imza, ust, [ust], kalin, normal, alt_bicim=normal))
        # Virgülsüz kalın ad başlık olabilir ("Mavi Vatan", Sosyal 6)
        self.assertFalse(imza_mi(blok(3, (56, 347, 200, 360), "Mavi Vatan", "kisa"), ust, [ust], kalin, normal))

    def test_v3_eser_adinda_rakam_olabilir(self):
        self.assertTrue(ad_gibi_mi("Metin And, 100 Soruda Türk Tiyatrosu Tarihi"))
        self.assertFalse(ad_gibi_mi("Görsel 1.19"))

    def test_v3_alinti_onceki_sayfalara_uzanir(self):
        def b(sayfa, no, bbox, metin, tur="paragraf"):
            return Blok(sayfa, no, bbox, metin, str(sayfa), tur)
        bloklar = [b(1, 1, (51, 68, 365, 95), "1. Okuma Metni (Ana Metin) HUZUR"), b(1, 2, (57, 123, 512, 700), SIIR),
                   b(2, 1, (57, 30, 120, 42), "3. Tema", "kisa"), b(2, 2, (57, 63, 512, 600), SIIR),
                   b(2, 3, (372, 694, 505, 707), "Ahmet Hamdi Tanpınar, Huzur", "kisa")]
        bicim = {(1, 1): ("MyriadPro-Bold", 11), (1, 2): ("MyriadPro-Regular", 10), (2, 1): ("MyriadPro-Regular", 10),
                 (2, 2): ("MyriadPro-Regular", 10), (2, 3): ("MyriadPro-Bold", 10)}
        self.assertEqual(set(alinti_bloklari(bloklar, bicim)), {(1, 2), (2, 1), (2, 2)})  # başlıkta durur

    def test_eski_dil(self):
        from derskitabi.kriterler.yazim import varsayilan_denetciler
        den = varsayilan_denetciler()
        self.assertTrue(eski_dil_mi(blok(1, (0, 0, 1, 1), "Yandı kandîl-i sipihrün cigeri döne döne"), den))
        self.assertTrue(eski_dil_mi(blok(1, (0, 0, 1, 1), "Niçeler tâc u tahtı mâl u mülkü koyup uryân olupdur"), den))
        # Modern metin, özel adda kısa çizgi: eski dil değil
        self.assertFalse(eski_dil_mi(blok(1, (0, 0, 1, 1), "Hacı Bayram-ı Velî Ankara'da yaşamış bir şairdir."), den))


class ReplikTesti(unittest.TestCase):
    def test_tiyatro_ve_hikaye_replikleri(self):
        oyun = [blok(i, (57, 100 + 20 * i, 300, 112 + 20 * i), m) for i, m in enumerate(
            ["KARAGÖZ — Bunu böyle söylesene!", "HACİVAT — Efendim, geçen gün evde otururken",
             "KARAGÖZ — Boza içerken genzine tarçın mı gitti?", "ll. HANIM — Bize bir mektup yazacaksınız."], start=1)]
        self.assertEqual(set(replik_bloklari(oyun)), {(1, 1), (1, 2), (1, 3), (1, 4)})
        hikaye = [blok(i, (57, 100 + 20 * i, 300, 112 + 20 * i), m) for i, m in enumerate(
            ["— Hangi kapıya gidecekmişiz peki?", "— Neler sorarlar içerde ağabeyim?", "— Sen gidince örtecek o mu?"], start=1)]
        self.assertEqual(len(replik_bloklari(hikaye)), 3)

    def test_icindekiler_ve_kisaltmalar_replik_degil(self):
        icindekiler = [blok(i, (57, 100 + 20 * i, 300, 112 + 20 * i), m) for i, m in enumerate(
            ["OKUMA: ŞİİR 15", "OKUMA: HİKÂYE 75", "EDEBİYAT ATÖLYESİ: YAZMA 51"], start=1)]
        hormonlar = [blok(i, (57, 100 + 20 * i, 300, 112 + 20 * i), m) for i, m in enumerate(
            ["ACTH: Böbrek üstü bezini uyarır.", "ADH: Su geri emilimini artırır.", "FSH: Folikülü olgunlaştırır."], start=1)]
        iki_replik = [blok(1, (57, 100, 300, 112), "HARPAGON: Paramı çaldılar!"),
                      blok(2, (57, 120, 300, 132), "VALÈRE: Ne oldu efendim?")]
        self.assertEqual(replik_bloklari(icindekiler), {})
        self.assertEqual(replik_bloklari(hormonlar), {})  # her etiket bir kez: tanım listesi (Biyoloji 11)
        self.assertEqual(replik_bloklari(iki_replik), {})  # sayfada en az 3 replik


class IsaretlemeTesti(unittest.TestCase):
    def test_yalniz_alintidaki_kelime_tespitleri_iner(self):
        t = [Tespit(1, 2, (0, 0, 1, 1), "yazim", "a", 1.0, alt_tur="morfoloji", metin_parcasi="sipihrün"),
             Tespit(1, 2, (0, 0, 1, 1), "yazim", "b", 1.0, alt_tur="noktalama_bosluk", metin_parcasi="x.Y"),
             Tespit(1, 3, (0, 0, 1, 1), "yazim", "c", 1.0, alt_tur="morfoloji", metin_parcasi="kisisel")]
        sonuc = alintilari_isaretle(t, {(1, 2): "Necâtî"})
        self.assertEqual([x.guven_skoru for x in sonuc], [DUSUK_GUVEN, 1.0, 1.0])
        self.assertIn(ALINTI_NOTU, sonuc[0].aciklama)
        self.assertIn("Necâtî", sonuc[0].aciklama)


if __name__ == "__main__":
    unittest.main()
