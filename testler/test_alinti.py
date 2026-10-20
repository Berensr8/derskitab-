"""Alıntı ayırma testleri (K28). Çalıştırma: python -m unittest -v"""

import unittest

from derskitabi.kriterler.alinti import (ALINTI_NOTU, DUSUK_GUVEN, ad_gibi_mi, alinti_bloklari,
                                         alintilari_isaretle, eski_dil_mi, imza_mi)
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
        for imza in ("Hüseyin Nihal Atsız", "Bedri Rahmi Eyüboğlu, Karadut", "Neclâ Pekolcay",
                     "Anonim (haz.: Mutlu Güleryüzlü)", "Karacaoğlan", "Mehmet Kaplan, Şiir Tahlilleri"):
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
        self.assertTrue(imza_mi(imza, ust, ("Avenir-Roman", 9), ("Avenir-Roman", 10)))
        # Aynı punto: imza değil (başlık ya da metnin devamı olabilir)
        self.assertFalse(imza_mi(imza, ust, ("Avenir-Roman", 10), ("Avenir-Roman", 10)))
        # Harita etiketi kadar küçük yazı: imza değil
        self.assertFalse(imza_mi(imza, ust, ("Arial", 3), ("Avenir-Roman", 10)))

    def test_imzanin_ustundeki_ayni_bicimli_bloklar_alinti(self):
        bloklar = [blok(1, (60, 100, 500, 130), METIN), blok(2, (183, 150, 384, 300), SIIR),
                   blok(3, (183, 302, 360, 320), "(...)", "kisa"), blok(4, (183, 322, 384, 600), SIIR),
                   blok(5, (255, 605, 384, 618), "Bedri Rahmi Eyüboğlu, Karadut", "kisa")]
        bicim = {(1, 1): ("Baskerville", 10), (1, 2): ("Avenir-Roman", 10), (1, 3): ("Avenir-Book", 10),
                 (1, 4): ("Avenir-Roman", 10), (1, 5): ("Avenir-Roman", 9)}
        al = alinti_bloklari(bloklar, bicim)
        self.assertEqual(set(al), {(1, 2), (1, 4)})  # "(...)" atlanır, farklı biçimli açıklama alıntı değil
        self.assertEqual(al[(1, 2)], "Bedri Rahmi Eyüboğlu, Karadut")

    def test_eski_dil(self):
        from derskitabi.kriterler.yazim import varsayilan_denetciler
        den = varsayilan_denetciler()
        self.assertTrue(eski_dil_mi(blok(1, (0, 0, 1, 1), "Yandı kandîl-i sipihrün cigeri döne döne"), den))
        self.assertTrue(eski_dil_mi(blok(1, (0, 0, 1, 1), "Niçeler tâc u tahtı mâl u mülkü koyup uryân olupdur"), den))
        # Modern metin, özel adda kısa çizgi: eski dil değil
        self.assertFalse(eski_dil_mi(blok(1, (0, 0, 1, 1), "Hacı Bayram-ı Velî Ankara'da yaşamış bir şairdir."), den))


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
