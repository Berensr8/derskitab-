"""Donanım bekçisi testleri (gerçek pil/sıcaklık okunmaz, sahteleri verilir)."""

import unittest

from derskitabi import donanim
from derskitabi.donanim import Bekci


class BekciTesti(unittest.TestCase):
    def kur(self, prizde, sicakliklar):
        self.uyumalar, self.mesajlar = [], []
        sicaklik = iter(sicakliklar)
        return Bekci(yaz=self.mesajlar.append, uyku=self.uyumalar.append,
                     prizde=prizde, sicaklik=lambda: next(sicaklik, 40), bos_ram=lambda: 10.0)

    def test_normal_durumda_beklemez(self):
        b = self.kur(lambda: True, [])
        for _ in range(donanim.KONTROL_ARALIGI):
            b.adim()
        self.assertEqual(self.uyumalar, [])

    def test_pildeyken_prize_takilana_kadar_bekler(self):
        durumlar = iter([False, False, True])
        b = self.kur(lambda: next(durumlar, True), [])
        for _ in range(donanim.KONTROL_ARALIGI):
            b.adim()
        self.assertEqual(self.uyumalar, [donanim.BEKLEME_SN])
        self.assertIn("pilde", self.mesajlar[0])

    def test_sicakken_soguyana_kadar_bekler(self):
        b = self.kur(lambda: True, [90, 80, 70])
        for _ in range(donanim.KONTROL_ARALIGI):
            b.adim()
        self.assertEqual(self.uyumalar, [donanim.BEKLEME_SN])  # 80 > 72 bekledi, 70'te devam

    def test_belirli_araliklarla_mola(self):
        b = self.kur(lambda: True, [])
        for _ in range(donanim.DINLENME_ARALIGI):
            b.adim()
        self.assertEqual(self.uyumalar, [donanim.DINLENME_SN])

    def test_bellek_azsa_bosalana_kadar_bekler(self):
        b = self.kur(lambda: True, [])
        ram = iter([1.0, 2.0, 5.0])
        b.bos_ram = lambda: next(ram, 5.0)
        for _ in range(donanim.KONTROL_ARALIGI):
            b.adim()
        self.assertEqual(self.uyumalar, [donanim.BEKLEME_SN])  # 2,0 < 3,0 bekledi; 5,0'te devam
        self.assertIn("bellek", self.mesajlar[0].lower())

    def test_kontrol_edilemezse_durdurmaz(self):
        b = self.kur(lambda: None, [])
        b.sicaklik = lambda: None
        b.bos_ram = lambda: None
        for _ in range(donanim.KONTROL_ARALIGI):
            b.adim()
        self.assertEqual(self.uyumalar, [])


if __name__ == "__main__":
    unittest.main()
