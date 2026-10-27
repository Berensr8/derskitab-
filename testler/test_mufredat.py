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

    def test_tema_kapagi_kapsam_sayilmaz(self):
        # Biyoloji 10 s.15: kapak programın içerik çerçevesini ve anahtar kavramlarını aynen aktarıyor
        kapak = [Blok(5, 1, (50, 50, 500, 60), "İÇERİK ÇERÇEVESİ", "5", "kisa"),
                 Blok(5, 2, (50, 70, 500, 130), "Güneşten besinlere: fotosentez, kemosentez, hücresel solunum, "
                      "aktif taşıma ve ökaryot hücrelerde enerji aktarımında ATP'nin rolü işlenir.", "5", "paragraf")]
        self.assertEqual(mufredat.tanitim_sayfalari(kapak + BLOKLAR), {5})
        self.assertEqual([b.sayfa_no for b in mufredat.paragraflar(kapak + BLOKLAR)], [10, 11, 12])
        self.assertEqual(mufredat.kavram_sayfalari(["ökaryot", "aktif taşıma"], kapak + BLOKLAR),
                         {"ökaryot": [], "aktif taşıma": [12]})
        self.assertFalse(mufredat.tanitim_sayfalari([Blok(9, 1, (0, 0, 1, 1), "1. Tema / ENERJİ", "9", "kisa")]))


    def test_cok_kelimeli_kavram_kelimeleri_ayni_sayfada(self):
        # Biyoloji 11: "kan basıncı dengesi" kitapta "kan basıncını düzenleyen…denge" olarak işleniyor
        b = [Blok(30, 1, (0, 0, 1, 1), "Böbrekler kan basıncını düzenleyen hormonlarla vücudun su dengesini korur.", "30", "paragraf")]
        self.assertEqual(mufredat.kavram_sayfalari(["kan basıncı dengesi", "sivil toplum kuruluşu (STK)"], b),
                         {"kan basıncı dengesi": [30], "sivil toplum kuruluşu (STK)": []})
        self.assertEqual(mufredat._bicimler("üretim-dağıtım-tüketim"), ["üretim dağıtım tüketim"])
        self.assertEqual(mufredat._bicimler("sivil toplum kuruluşu (STK)"), ["sivil toplum kuruluşu", "STK"])

    def test_program_altligi_kavrama_karismaz(self):
        self.assertEqual(mufredat._sade("töre 77 SOSYAL BİLGİLER DERSİ ÖĞRETİM PROGRAMI"), "töre")


class KavramKontroluTesti(unittest.TestCase):
    def test_eksik_kavram_ve_eksik_tema(self):
        ciktilar = [Cikti("BİY.10.1.1", 10, 1, "Fotosentez", "", ["fotosentez", "kloroplast", "ökaryot"]),
                    Cikti("BİY.10.2.1", 10, 2, "Ekosistem", "", ["besin zinciri", "biyom", "süksesyon", "biyolojik birikim"])]
        tespitler = mufredat.kavram_kontrolu(BLOKLAR, ciktilar)
        self.assertEqual(sorted((t.alt_tur, t.metin_parcasi) for t in tespitler),
                         [("kavram_yok", "ökaryot"), ("tema_yok", "BİY.10.2")])  # 3/4 kavram yok: tek tema notu
        self.assertIn("başka bir ciltte", next(t for t in tespitler if t.alt_tur == "tema_yok").aciklama)


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
