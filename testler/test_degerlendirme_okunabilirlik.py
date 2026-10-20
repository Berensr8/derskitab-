"""Okunabilirlik değerlendirmesi (K24) testleri."""

import unittest

from derskitabi.degerlendirme import set_yukle
from derskitabi.degerlendirme_okunabilirlik import EKLEME_SHA256, EKLEME_YOLU, auc


class AucTesti(unittest.TestCase):
    def test_kusursuz_ve_yazi_tura(self):
        self.assertEqual(auc([1, 2], [5, 6], dusuk_zor=True), 1.0)  # zor grubun puanları hep daha düşük
        self.assertEqual(auc([3, 3], [3, 3], dusuk_zor=True), 0.5)
        self.assertEqual(auc([9, 8], [1, 2], dusuk_zor=False), 1.0)  # Bezirci: yüksek = zor


class KilitTesti(unittest.TestCase):
    def test_eklemeler_kilitlendigi_gibi(self):
        self.assertEqual(len(set_yukle(EKLEME_YOLU, EKLEME_SHA256)), 60)


if __name__ == "__main__":
    unittest.main()
