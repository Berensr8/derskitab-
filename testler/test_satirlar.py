"""Satır bloklarını birleştirme testleri. Çalıştırma: python -m unittest -v"""

import unittest

from derskitabi.model import Blok
from derskitabi.satirlar import birlesik_bloklar, grup_metni, satir_gruplari


def satir(no, y, metin, x0=43, x1=388, sayfa=101):
    return Blok(sayfa, no, (x0, y, x1, y + 12), metin, "100", "paragraf" if len(metin.split()) >= 5 else "kisa")


# TDE 12, s.101: biyografi kutusunda her satır ayrı blok
BIYOGRAFI = [satir(13, 528, "eğitimini yarıda bıraktı. 1936’da Ankara’da memurluk yapmaya başladı. 1 Ocak"),
             satir(14, 542, "1949’dan 15 Haziran 1950’ye kadar Yaprak dergisini çıkardı. Orhan Veli’nin Garip"),
             satir(15, 556, "tarzında yazdığı ilk şiirleri 1937’de Varlık dergisinde yayımlandı. Şiirlerinde beş", x1=386),
             satir(16, 570, "duyuyla algıladığı yaşamı birçok ayrıntıya yer vererek dile getirdi.", x1=300)]


class SatirTesti(unittest.TestCase):
    def test_biyografi_satirlari_tek_paragraf(self):
        gruplar = satir_gruplari(BIYOGRAFI)
        self.assertEqual([[b.blok_no for b in g] for g in gruplar], [[13, 14, 15, 16]])
        metin, baslar = grup_metni(gruplar[0])
        self.assertIn("Orhan Veli’nin Garip tarzında yazdığı ilk şiirleri 1937’de", metin)
        self.assertEqual(metin[baslar[2]:baslar[2] + 8], "tarzında")

    def test_kunye_ad_listesi_birlesmez(self):
        kunye = [satir(1, 100, "Dil Uzmanı", x1=120), satir(2, 114, "Emel ERKİN", x1=118)]
        self.assertEqual(len(satir_gruplari(kunye)), 2)

    def test_liste_maddesi_ve_uzak_blok_birlesmez(self):
        bloklar = [satir(1, 100, "Görseldeki materyaller yerine farklı materyaller de kullanılabilir ve"),
                   satir(2, 114, "a) hazırlayacağınız sokağa edebiyatçıların adlarını veriniz.")]
        self.assertEqual(len(satir_gruplari(bloklar)), 2)
        uzak = [satir(1, 100, "Görseldeki materyaller yerine farklı materyaller de kullanılabilir ve"),
                satir(2, 160, "ayrıca öğretmeninizin önerdiği başka materyaller de olabilir.")]
        self.assertEqual(len(satir_gruplari(uzak)), 2)

    def test_tiresi_kaybolmus_kelime(self):
        a, b = satir(1, 100, "başlayan Anday, 1937’den itibaren Ga"), satir(2, 114, "rip tarzında şiirler yazdı.")
        metin, _ = grup_metni([a, b], bilesik_mi=lambda k: k in {"garip", "Garip", "tarzında"})
        self.assertIn("itibaren Garip tarzında", metin)

    def test_satir_sonu_tiresi_silinir(self):
        a, b = satir(1, 100, "sürdürülebilir olmasına ve top-"), satir(2, 114, "lumsal fayda sağlayacak nitelikler taşımasına")
        self.assertIn("ve toplumsal fayda", grup_metni([a, b])[0])
        c = satir(2, 114, "Yunan ilişkileri gelişti ve yeni bir dönem başladı.")
        self.assertIn("Türk-Yunan", grup_metni([satir(1, 100, "bu dönemde Türk-"), c])[0])  # büyük harf: gerçek tire

    def test_birlesik_blok_ilk_numarayi_ve_kutuyu_alir(self):
        b = birlesik_bloklar(BIYOGRAFI)
        self.assertEqual(len(b), 1)
        self.assertEqual((b[0].blok_no, b[0].bbox[1], b[0].bbox[3], b[0].tur), (13, 528, 582, "paragraf"))


if __name__ == "__main__":
    unittest.main()
