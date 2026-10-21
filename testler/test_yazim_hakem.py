"""Yazım hakemi (K25) testleri: sahte hakemle (dil modeli yüklenmez)."""

import unittest

from derskitabi.kriterler.yazim_hakem import DUSUK_GUVEN, baglam, hakemle
from derskitabi.model import Blok, Tespit

BLOK = Blok(5, 1, (0, 0, 1, 1), "Hücreler enerji üretir. Glikoliz sitoplazmada gerçekleşir ve kisisel bir bilgi değildir.",
            "5", "paragraf")


SOZLUK = {"hücreler", "enerji", "üretir", "sitoplazmada", "gerçekleşir", "ve", "bir", "bilgi", "değildir",
          "jandarma", "atlı", "timleri"}
DENETCI = (lambda k: k in SOZLUK, lambda k: k in SOZLUK)


def tespit(parca, guven=1.0, alt_tur="morfoloji"):
    return Tespit(5, 1, BLOK.bbox, "yazim", "Çözümlenemedi.", guven, alt_tur=alt_tur, metin_parcasi=parca)


def sahte_hakem(kayit):
    def hakem(kelime, cumle, onceki):
        kayit.append((kelime, cumle, onceki))
        return ({"karar": "dogru", "aciklama": "Biyoloji terimi.", "oneri": ""} if kelime == "Glikoliz"
                else {"karar": "hata", "aciklama": "Ş yerine s.", "oneri": "kişisel"})
    return hakem


class HakemTesti(unittest.TestCase):
    def test_dogru_denen_dusuk_oncelige_iner_silinmez(self):
        sonuc = hakemle([tespit("Glikoliz")], [BLOK], sahte_hakem([]), denetciler=DENETCI)
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sonuc[0].guven_skoru, DUSUK_GUVEN)
        self.assertIn("muhtemelen doğru", sonuc[0].aciklama)

    def test_hata_denen_korunur_ve_oneri_eklenir(self):
        sonuc = hakemle([tespit("kisisel", 0.5)], [BLOK], sahte_hakem([]), denetciler=DENETCI)
        self.assertEqual(sonuc[0].guven_skoru, 0.75)  # tek araç + hakem hemfikir
        self.assertIn("kişisel", sonuc[0].aciklama)

    def test_kural_tespitine_dokunulmaz_ve_girdi_degismez(self):
        kural = tespit("kitap ta,", alt_tur="bag_te_ta")
        girdi = [kural, tespit("Glikoliz")]
        kayit = []
        sonuc = hakemle(girdi, [BLOK], sahte_hakem(kayit), denetciler=DENETCI)
        self.assertIs(sonuc[0], kural)
        self.assertEqual([k[0] for k in kayit], ["Glikoliz"])
        self.assertEqual(girdi[1].guven_skoru, 1.0)  # asıl liste değişmedi

    def test_onbellekteki_kelime_yeniden_sorulmaz(self):
        kayit, onbellek = [], {}
        hakemle([tespit("Glikoliz")], [BLOK], sahte_hakem(kayit), onbellek=onbellek, denetciler=DENETCI)
        hakemle([tespit("Glikoliz")], [BLOK], sahte_hakem(kayit), onbellek=onbellek, denetciler=DENETCI)
        self.assertEqual(len(kayit), 1)

    def test_model_dogru_dese_de_kitaptaki_kelimeye_tek_harf_yakinsa_dusurulmez(self):
        # Dil modeli "jandama"yı "jandarma" diye okuyup doğru dedi (K25 geliştirme verisi)
        blok = Blok(7, 1, (0, 0, 1, 1), "Atlı jandama timleri görev yapar. Jandarma eğitimi verilir.", "7", "paragraf")
        hakem = lambda kelime, cumle, onceki: {"karar": "dogru", "aciklama": "", "oneri": ""}  # noqa: E731
        t = Tespit(7, 1, blok.bbox, "yazim", "x", 1.0, alt_tur="morfoloji", metin_parcasi="jandama")
        sonuc = hakemle([t], [blok], hakem, denetciler=DENETCI)
        self.assertEqual(sonuc[0].guven_skoru, 0.5)
        self.assertIn("jandarma", sonuc[0].aciklama)

    def test_son_harf_silinmesi_ve_rastgele_degisim_komsu_sayilmaz(self):
        from derskitabi.kriterler.yazim_hakem import _yazim_hatasi_komsulari
        komsular = _yazim_hatasi_komsulari("grid")
        self.assertNotIn("gri", komsular)  # son harf silinmesi
        self.assertNotIn("brid", komsular)  # rastgele harf değişimi
        self.assertIn("gird", komsular)  # yer değiştirme
        self.assertIn("kişisel", _yazim_hatasi_komsulari("kisisel"))  # Türkçe harf

    def test_hece_ikilenmesi_ve_dusmesi_komsu_sayilir(self):
        # K29 eki: model "olacacağını" ve "sorumluklar"ın üzerinden okuyup "doğru" demişti
        from derskitabi.kriterler.yazim_hakem import _yazim_hatasi_komsulari
        self.assertIn("olacağını", _yazim_hatasi_komsulari("olacacağını"))
        self.assertIn("sorumluluklar", _yazim_hatasi_komsulari("sorumluklar"))
        self.assertNotIn("oma", _yazim_hatasi_komsulari("omuza"))  # rastgele iki harf silinmesi değil

    def test_baglam_cumle_ve_onceki_cumle(self):
        cumle, onceki = baglam(BLOK.metin, "kisisel")
        self.assertTrue(cumle.startswith("Glikoliz"))
        self.assertEqual(onceki, "Hücreler enerji üretir.")


if __name__ == "__main__":
    unittest.main()
