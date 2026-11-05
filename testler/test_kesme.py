"""Kesme işareti denetimi testleri (K34). Zemberek yerine küçük sahte çözümleyici kullanılır."""

import unittest
from collections import Counter

from derskitabi.kriterler.kesme import gereksiz_kesme, kesme_denetimi, ozel_ad_eki
from derskitabi.model import Blok

P = "[{k}:Noun, Prop] {l}:Noun+A3sg"
CEVAP = {
    "türkistanda": [P.format(k="Türkistan", l="türkistan") + "+da:Loc"],
    "atatürkün": [P.format(k="Atatürk", l="atatürk") + "+ün:Gen", P.format(k="Atatürk", l="atatürk") + "+ün:P2sg"],
    "ankaradaki": [P.format(k="Ankara", l="ankara") + "+da:Loc|ki:Rel→Adj"],
    "ankaradır": [P.format(k="Ankara", l="ankara") + "|Zero→Verb+Pres+A3sg+dır:Cop"],
    "doğuda": ["[doğu:Noun] doğu:Noun+A3sg+da:Loc", P.format(k="Doğu", l="doğu") + "+da:Loc"],
    "türklerin": ["[Türk:Noun, Prop] türk:Noun+ler:A3pl+in:Gen"],
    "konyalıdan": [P.format(k="Konya", l="konya") + "|lı:With→Adj|Zero→Noun+A3sg+dan:Abl"],
    "kerküğe": [P.format(k="Kerkük", l="kerkük") + "+e:Dat"],
    "mayısın": [P.format(k="Mayıs", l="mayıs") + "+ın:Gen"],
    "türk": [P.format(k="Türk", l="türk")],
    "türkler": ["[Türk:Noun, Prop] türk:Noun+ler:A3pl"],
    "oğuzlar": [P.format(k="Oğuzlar", l="oğuzlar"), "[Oğuz:Noun, Prop] oğuz:Noun+lar:A3pl"],
    "oğuz": [P.format(k="Oğuz", l="oğuz")],
    "türkçe": ["[Türk:Noun, Prop] türk:Noun+A3sg+çe:Equ", P.format(k="Türkçe", l="türkçe")],
    "tibete": [P.format(k="Tibet", l="tibet") + "+e:Dat"],
    "halide": [P.format(k="Halid", l="halid") + "+e:Dat"],
    "ömerî": [P.format(k="Ömer", l="ömer") + "+î:Acc"],
}


def cozumle(k: str) -> list[str]:
    return CEVAP.get(k.replace("I", "ı").replace("İ", "i").lower(), [])


def blok(metin: str) -> Blok:
    return Blok(1, 1, (0, 0, 1, 1), metin, "1", "paragraf")


HER_AD = Counter({"Türkistan": 1, "Atatürk": 1, "Ankara": 1, "Kerkük": 1, "Tibet": 1, "Halid": 1, "Mayıs": 1})


def bulunan(metin: str, kesmeli: Counter = HER_AD) -> list[tuple[str, str]]:
    return [(t.alt_tur, t.metin_parcasi) for t in kesme_denetimi(blok(metin), kesmeli, cozumle)]


class OzelAdTesti(unittest.TestCase):
    def test_cekim_ve_bildirme_eki(self):
        self.assertEqual(ozel_ad_eki("Türkistanda", cozumle), "Türkistan'da")
        self.assertEqual(ozel_ad_eki("Atatürkün", cozumle), "Atatürk'ün")
        self.assertEqual(ozel_ad_eki("Ankaradaki", cozumle), "Ankara'daki")
        self.assertEqual(ozel_ad_eki("Ankaradır", cozumle), "Ankara'dır")
        self.assertEqual(ozel_ad_eki("Kerküğe", cozumle), "Kerkük'e")

    def test_tdk_istisnalari(self):
        self.assertIsNone(ozel_ad_eki("Doğuda", cozumle))  # cins ad okuması da var
        self.assertIsNone(ozel_ad_eki("Türklerin", cozumle))  # çokluk eki
        self.assertIsNone(ozel_ad_eki("Konyalıdan", cozumle))  # yapım eki
        self.assertIsNone(ozel_ad_eki("Mayısın", cozumle))  # ay adı: yalnız belirli tarihte
        self.assertIsNone(ozel_ad_eki("Ömerî", cozumle))  # şapkalı harf ek değil

    def test_kitapta_kesmeli_yazilmamis_ad_isaretlenmez(self):
        self.assertEqual(bulunan("Ordu Tibete ulaştı.", Counter()), [])
        self.assertEqual(bulunan("Ordu Tibete ulaştı.", Counter({"Tibet": 2})), [("ozel_ad_kesme", "Tibete")])

    def test_cok_kelimeli_adin_ici_isaretlenmez(self):
        self.assertEqual(bulunan("Halide Nusret yazdı."), [])
        self.assertEqual(bulunan("Bu Halide yazdığı mektup."), [("ozel_ad_kesme", "Halide")])

    def test_eser_listesi_isaretlenmez(self):
        self.assertEqual(bulunan("Eserleri: Yâd, Arz-ı Hal, Tibete, Dünyanın En Güzel Kitabı, Tütünler"), [])
        self.assertEqual(bulunan("Özker Yaşın, Yeşilada’nın Tibete yiğit, özgür sesidir."),
                         [("ozel_ad_kesme", "Tibete")])

    def test_kesmeli_yazim_isaretlenmez(self):
        self.assertEqual(bulunan("Türkistan’da ve Atatürk'ün"), [])


class KisaltmaSayiTesti(unittest.TestCase):
    def test_kisaltma_ve_sayi(self):
        self.assertEqual(bulunan("DNAnın yapısı 1923te bulundu, 19uncu yüzyıl."),
                         [("kisaltma_kesme", "DNAnın"), ("sayi_kesme", "1923te"), ("sayi_kesme", "19uncu")])

    def test_dogrular_ve_degiskenler(self):
        self.assertEqual(bulunan("DNA'nın yapısı 1923'te, 3a + 2b, 1990'lı yıllar, ABD’de, 5 km'de."), [])


class GereksizKesmeTesti(unittest.TestCase):
    def test_yapim_ve_cokluk_eki(self):
        self.assertIsNotNone(gereksiz_kesme("Konya", "lı", cozumle))
        self.assertIsNotNone(gereksiz_kesme("Türkler", "in", cozumle))
        self.assertIsNotNone(gereksiz_kesme("Türkçe", "nin", cozumle))

    def test_dogru_kesmeler(self):
        self.assertIsNone(gereksiz_kesme("Oğuzlar", "ın", cozumle))  # sözlükte ad olarak var
        self.assertIsNone(gereksiz_kesme("Atatürk", "ün", cozumle))
        self.assertIsNone(gereksiz_kesme("Osmanlı", "nın", cozumle))  # TDK: Karakeçili'nin


if __name__ == "__main__":
    unittest.main()
