"""Yazım değerlendirmesi (K23) testleri."""

import unittest

from derskitabi.degerlendirme_yazim import KILIT_SHA256, SET_YOLU as YAZIM_SET, bulundu_mu
from derskitabi.degerlendirme import set_yukle
from derskitabi.model import Tespit


def tespit(alt_tur, parca, guven=1.0, sayfa=5, blok=2):
    return Tespit(sayfa, blok, (0, 0, 1, 1), "yazim", "a", guven, alt_tur=alt_tur, metin_parcasi=parca)


class BulunduTesti(unittest.TestCase):
    def test_kelime_hatasi(self):
        oge = {"sayfa_no": 5, "blok_no": 2, "alt_tur": "dusme", "beklenen_alt_tur": "morfoloji", "aranan": "aldğı"}
        self.assertEqual(bulundu_mu(oge, [tespit("morfoloji", "aldğı", 0.5)]), 0.5)
        self.assertEqual(bulundu_mu(oge, [tespit("morfoloji", "aldğı", blok=3)]), 0.0)  # başka blok

    def test_noktalama_parcasi_isaretin_cevresine_bakar(self):
        oge = {"sayfa_no": 5, "blok_no": 2, "alt_tur": "noktalama_bosluk", "beklenen_alt_tur": "noktalama_bosluk",
               "aranan": "monosakkaritlere,yağlar"}
        self.assertEqual(bulundu_mu(oge, [tespit("noktalama_bosluk", "sakkaritlere,yağlar glise")]), 1.0)


class KilitTesti(unittest.TestCase):
    def test_yazim_seti_kilitlendigi_gibi(self):
        ogeler = set_yukle(YAZIM_SET, KILIT_SHA256)
        self.assertEqual((len(ogeler), sum(o["set"] == "test" for o in ogeler)), (80, 56))


if __name__ == "__main__":
    unittest.main()
