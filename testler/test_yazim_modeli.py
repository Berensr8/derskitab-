"""Yazım modeli veri hazırlığı testleri (K33). Çalıştırma: python -m unittest -v

Eğitim ve ölçüm (torch, ekran kartı) burada sınanmaz; yalnız veri tarafı."""

import random
import unittest

from derskitabi.yazim_modeli import sentetik, vikipedi
from derskitabi.yazim_modeli.etiketler import SINIF_NO, gecturk_sinifi


class VikipediTesti(unittest.TestCase):
    def test_yazim_duzeltmesi_etiketlenir(self):
        eski = "Bu şehir [[İç Anadolu]]da yer alır ve kisisel gelisim için önemlidir. Nüfusu fazladır."
        yeni = "Bu şehir [[İç Anadolu]]'da yer alır ve kişisel gelişim için önemlidir. Nüfusu fazladır."
        o = vikipedi.satir_ornekleri(eski, yeni)
        etiketli = {w: e for w, e in zip(o[0]["kelimeler"], o[0]["etiketler"]) if e}
        self.assertEqual(etiketli, {"Anadoluda": SINIF_NO["KURAL_DIGER"], "kisisel": SINIF_NO["HARF"],
                                    "gelisim": SINIF_NO["HARF"]})
        self.assertEqual(o[0]["duzeltmeler"]["8"], "gelişim")

    def test_bitisik_ayri_ve_buyuk_harf(self):
        o = vikipedi.satir_ornekleri("Kitabı her hangi bir yerde bulabilirsiniz dedi ankara valisi.",
                                     "Kitabı herhangi bir yerde bulabilirsiniz dedi Ankara valisi.")
        self.assertEqual([e for e in o[0]["etiketler"] if e],
                         [SINIF_NO["BITISIK_AYRI"]] * 2 + [SINIF_NO["BUYUK_KUCUK"]])

    def test_anlam_degisikligi_satiri_atilir(self):
        self.assertIsNone(vikipedi.satir_ornekleri("Bu şehir çok güzel bir yerdir ve herkes sever.",
                                                   "Bu kent çok güzel bir yerdir ve herkes sever."))
        self.assertIsNone(vikipedi.satir_ornekleri("Nüfus 1990 yılında 5000 kişiydi ve arttı.",
                                                   "Nüfus 1990 yılında 6000 kişiydi ve arttı."))

    def test_viki_bicimi_temizlenir(self):
        self.assertEqual(vikipedi.temizle("'''Ankara''' [[Türkiye|Türkiye'nin]] başkenti{{kaynak}}<ref>x</ref>."),
                         "Ankara Türkiye'nin başkenti .")

    def test_fark_tablosu_okunur(self):
        h = ('<tr><td class="diff-marker"></td><td class="diff-deletedline diff-side-deleted"><div>bir '
             '<del class="diffchange diffchange-inline">kaç</del> lisan</div></td><td class="diff-marker"></td>'
             '<td class="diff-addedline diff-side-added"><div>birkaç lisan</div></td></tr>')
        self.assertEqual(vikipedi.fark_satirlari(h), [("bir kaç lisan", "birkaç lisan")])


class SentetikTesti(unittest.TestCase):
    def test_hata_eklenen_kelime_etiketli_digerleri_ayni(self):
        r = random.Random(3)
        cumle = "Öğrenciler kişisel gelişimlerini ve sorumluluklarını bu kitapta öğrenecekler.".split()
        for _ in range(50):
            o = sentetik.hata_ekle(cumle, r, 3)
            if o is None:
                continue
            kelimeler, etiketler = o
            self.assertEqual(len(kelimeler), len(etiketler))
            self.assertTrue(any(etiketler))
            for w, e in zip(kelimeler, etiketler):
                if not e:
                    self.assertIn(w, cumle)  # etiketsiz kelime değişmemiş olmalı

    def test_harf_hatasi_turleri(self):
        r = random.Random(1)
        sonuclar = {sentetik.harf_hatasi("sorumluluklarını", r) for _ in range(200)}
        self.assertIn("sorumluluklarini", sonuclar)  # Türkçe harf kaybı
        self.assertTrue(any(len(s) == len("sorumluluklarını") + 1 for s in sonuclar if s))  # ikileme


class EtiketTesti(unittest.TestCase):
    def test_gecturk_eslemesi(self):
        self.assertEqual(gecturk_sinifi(0), 0)
        self.assertEqual(gecturk_sinifi(22), SINIF_NO["BITISIK_AYRI"])  # hiç bir
        self.assertEqual(gecturk_sinifi(12), SINIF_NO["HARF"])  # başlıyacağım
        self.assertEqual(gecturk_sinifi(23), SINIF_NO["BUYUK_KUCUK"])


if __name__ == "__main__":
    unittest.main()
