"""Müfredat uyumu testleri (K31). Çalıştırma: python -m unittest -v"""

import unittest

import numpy as np

from derskitabi.kriterler import mufredat
from derskitabi.kriterler.mufredat import Cikti
from derskitabi.model import Blok

PARAGRAFLAR = [
    "Fotosentez, bitkilerin ışık enerjisini kullanarak karbondioksit ve sudan glikoz ürettiği süreçtir ve kloroplastta gerçekleşir.",
    "Ekosistemde enerji akışı üreticilerden tüketicilere doğru besin zinciri boyunca gerçekleşir ve her basamakta enerji azalır.",
    "Hücre zarı seçici geçirgen bir yapıdır; maddeler hücreye aktif taşıma ve pasif taşıma yollarıyla girip çıkar.",
]
BLOKLAR = [Blok(10 + i, 1, (50, 100, 500, 160), m, str(10 + i), "paragraf") for i, m in enumerate(PARAGRAFLAR)]


def sahte_gomucu(metinler):
    """Anahtar kelimelere göre üç boyutlu vektör: fotosentez, ekosistem, hücre zarı."""
    return np.array([[1.0 * ("fotosentez" in m.lower()) + 0.01, 1.0 * ("ekosistem" in m.lower()) + 0.01,
                      1.0 * ("zar" in m.lower() or "taşıma" in m.lower()) + 0.01] for m in metinler])


class ProgramTesti(unittest.TestCase):
    def test_kavram_ek_alabilir_ve_cok_kelimeli(self):
        sayfalar = mufredat.kavram_sayfalari(["aktif taşıma", "ökaryot", "besin zinciri"], BLOKLAR)
        self.assertEqual(sayfalar, {"aktif taşıma": [12], "ökaryot": [], "besin zinciri": [11]})
        self.assertTrue(mufredat._kavram_deseni("prokaryot").search("prokaryotlar ve ökaryotlar"))
        self.assertFalse(mufredat._kavram_deseni("dil").search("dilim ekmek"[:0] + "bildiri"))  # kelime içinde değil


class AnalizTesti(unittest.TestCase):
    def test_en_benzer_paragraflar_hakeme_gider_ve_karsilanmayan_tespit_olur(self):
        ciktilar = [Cikti("BİY.10.1.5", 10, 1, "Fotosentezin evrelerini açıklayabilme", "Fotosentez", ["ışık enerjisi"]),
                    Cikti("BİY.12.1.1", 12, 1, "Sinir sisteminin yapısını açıklayabilme", "Sinir sistemi", ["nöron"])]
        gorulen = {}

        def hakem(c, adaylar):
            gorulen[c.kod] = adaylar[0].sayfa_no
            return {"karar": "karsilaniyor" if c.kod.startswith("BİY.10") else "karsilanmiyor", "gerekce": "test"}

        kayit, tespitler = mufredat.analiz_et(BLOKLAR, ciktilar, gomucu=sahte_gomucu, hakem=hakem)
        self.assertEqual(gorulen["BİY.10.1.5"], 10)  # fotosentez paragrafı en benzer
        self.assertEqual([r["karar"] for r in kayit], ["karsilaniyor", "karsilanmiyor"])
        turler = sorted((t.alt_tur, t.metin_parcasi) for t in tespitler)
        self.assertEqual(turler, [("cikti_karsilanmiyor", "BİY.12.1.1"), ("kavram_yok", "nöron")])
        self.assertEqual(kayit[1]["eksik_kavramlar"], ["nöron"])


if __name__ == "__main__":
    unittest.main()
