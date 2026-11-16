"""Sayfa okuma (K48) testleri: sahte okuyucuyla (Ollama gerekmez)."""

import unittest

from derskitabi.kriterler import sayfa_okuma as so
from derskitabi.model import Blok, Tespit

B1 = Blok(5, 1, (0, 0, 1, 1), "Hücreler enerji üretir. Bitkiler solunumu gece gündüz fotosentezi yapar.", "3", "paragraf")
B2 = Blok(5, 2, (0, 2, 1, 3), "Adı Difüzyon ve Ozmoz Süre 80 dk.", "3", "paragraf")
B3 = Blok(5, 3, (0, 4, 1, 5), "Molekülün yapısı-", "3", "paragraf")
B4 = Blok(5, 4, (0, 6, 1, 7), "Atlar ve 1953’ te yıllar geçti.", "3", "paragraf")
B5 = Blok(5, 5, (0, 8, 1, 9), "Etsem de ‘abesdir sitem", "3", "paragraf")
BLOKLAR = [B1, B2, B3, B4, B5]


def okuyucu(adaylar, kayit=None):
    def f(baslik, metin):
        if kayit is not None:
            kayit.append((baslik, metin))
        return adaylar
    return f


def aday(k, o, g="Gerekçe"):
    return {"kitaptaki": k, "onerilen": o, "gerekce": g}


def calistir(adaylar, tespitler=(), **kw):
    return so.uygula(list(tespitler), BLOKLAR, okuyucu=okuyucu(adaylar), **kw)


class SuzgecTesti(unittest.TestCase):
    def test_gercek_aday_tespit_olur(self):
        sonuc, sayac = calistir([aday("gece gündüz fotosentezi", "gece gündüz, fotosentezi")])
        self.assertEqual(len(sonuc), 1)
        t = sonuc[0]
        self.assertEqual((t.kriter, t.alt_tur, t.guven_skoru, t.blok_no, t.sayfa_no), ("yazim", "sayfa_okuma", 0.5, 1, 5))
        self.assertEqual(t.metin_parcasi, "gece gündüz fotosentezi")
        self.assertEqual(t.basili_sayfa_no, "3")
        self.assertIn("Yerel dil modeli (gemma4) sayfayı okurken işaretledi", t.aciklama)
        self.assertIn("'gece gündüz fotosentezi' → 'gece gündüz, fotosentezi'", t.aciklama)
        self.assertIn("Gerekçe: Gerekçe.", t.aciklama)
        self.assertIn("ölçülmüş isabeti henüz bilinmiyor", t.aciklama)
        self.assertEqual(sayac["tespit"], 1)

    def test_kitapta_gecmeyen_aday_atilir(self):
        sonuc, sayac = calistir([aday("uydurma cümle", "başka cümle")])
        self.assertEqual(sonuc, [])
        self.assertEqual(sayac["kitapta_yok"], 1)

    def test_kitaptaki_bosluk_farkiyla_bulunur(self):
        sonuc, _ = calistir([aday("gece   gündüz\nfotosentezi", "gece gündüz, fotosentezi")])
        self.assertEqual(len(sonuc), 1)

    def test_filtre1_ayni_metin(self):
        sonuc, sayac = calistir([aday("Hücreler enerji üretir", "Hücreler  enerji\nüretir"),
                                 aday("Etsem de ‘abesdir", "Etsem de 'abesdir")])
        self.assertEqual(sonuc, [])
        self.assertEqual(sayac["ayni_metin"], 2)

    def test_bosluk_ve_harf_boyu_duzeltmesi_gercek_oneridir(self):
        # boşluk silme/ekleme ve büyük/küçük harf düzeltmesi "aynı" sayılmaz (K48 düzeltmesi)
        self.assertFalse(so.ayni_mi("1953’ te", "1953’te"))
        self.assertFalse(so.ayni_mi("Ksilem de", "Ksilemde"))
        self.assertFalse(so.ayni_mi("suv modeli", "SUV modeli"))
        sonuc, sayac = calistir([aday("1953’ te", "1953’te")])
        self.assertEqual((len(sonuc), sayac["ayni_metin"]), (1, 0))

    def test_filtre2_iki_nokta_ve_satir_sonu(self):
        sonuc, sayac = calistir([aday("Adı Difüzyon ve Ozmoz Süre 80 dk.", "Adı: Difüzyon ve Ozmoz\nSüre: 80 dk.")])
        self.assertEqual(sonuc, [])
        self.assertEqual(sayac["iki_nokta_satir_sonu"], 1)
        # iki nokta öncesindeki boşluğu düzeltmek sayfa düzeni değildir
        self.assertFalse(so.iki_nokta_satir_sonu_farki_mi("Yönerge :", "Yönerge:"))

    def test_satir_sonunda_bolunmus_kelime(self):
        self.assertTrue(so.satir_sonu_tiresi_mi("hazır\nlanması", "hazırlanması"))
        self.assertFalse(so.satir_sonu_tiresi_mi("hazır lanması", "hazırlanması"))

    def test_filtre3_satir_sonu_tiresi(self):
        sonuc, sayac = calistir([aday("yapısı-", "yapısı"), aday("yapısı-", "yapısı-nın"),
                                 aday("spektru-", "spektrum-")])
        # 'spektru-' kitapta yok: ilk iki satır sonu tiresi (ikincisi kelimeyi tamamlıyor), üçüncü kitapta yok
        self.assertEqual(sonuc, [])
        self.assertEqual(sayac["satir_sonu_tiresi"], 2)
        self.assertEqual(sayac["kitapta_yok"], 1)

    def test_tire_olmayan_ekleme_atilmaz(self):
        # tire bitişte değilse süzgeç 3 uygulanmaz
        self.assertFalse(so.satir_sonu_tiresi_mi("yapısı", "yapısını"))
        self.assertTrue(so.satir_sonu_tiresi_mi("spektru-", "spektrum-"))
        self.assertTrue(so.satir_sonu_tiresi_mi("manye-", "manyet-"))
        self.assertFalse(so.satir_sonu_tiresi_mi("yapısı-", "başka"))

    def test_filtre4_mevcut_tespitle_cakisma_not_ekler(self):
        mevcut = Tespit(5, 1, B1.bbox, "yazim", "Virgül eksik.", 0.75, "3", "liste_tutarsiz_virgul", "gece gündüz")
        sonuc, sayac = calistir([aday("gece gündüz fotosentezi", "gece gündüz, fotosentezi")], [mevcut])
        self.assertEqual(len(sonuc), 1)  # yeni tespit yok
        self.assertEqual(sonuc[0].guven_skoru, 0.75)  # öncelik değişmez
        self.assertIn("Sayfa okuma da işaretledi", sonuc[0].aciklama)
        self.assertEqual(sayac["mevcut_tespit"], 1)
        self.assertNotIn("Sayfa okuma", mevcut.aciklama)  # girdi nesnesi değişmez

    def test_mevcut_tespit_notu_tekrarlanmaz(self):
        mevcut = Tespit(5, 1, B1.bbox, "yazim", "x", 0.75, "3", "liste_tutarsiz_virgul", "gece gündüz")
        sonuc, _ = calistir([aday("gece gündüz fotosentezi", "gece gündüz, fotosentezi"),
                             aday("solunumu gece gündüz", "solunumu gece, gündüz")], [mevcut])
        self.assertEqual(sonuc[0].aciklama.count("Sayfa okuma da işaretledi"), 1)

    def test_baska_sayfadaki_tespitle_cakismaz(self):
        mevcut = Tespit(9, 1, B1.bbox, "yazim", "x", 0.75, "3", "liste_tutarsiz_virgul", "gece gündüz")
        sonuc, sayac = calistir([aday("gece gündüz fotosentezi", "gece gündüz, fotosentezi")], [mevcut])
        self.assertEqual(sayac["tespit"], 1)
        self.assertEqual(len(sonuc), 2)

    def test_alintida_guven_025(self):
        sonuc, sayac = calistir([aday("‘abesdir sitem", "abestir sitem")], alintilar={(5, 5): "Fuzûlî"})
        self.assertEqual(sonuc[0].guven_skoru, 0.25)
        self.assertIn("Alıntı metin", sonuc[0].aciklama)
        self.assertEqual(sayac["alinti_dusuk"], 1)

    def test_ayni_aday_tekrari_bir_tespit(self):
        sonuc, sayac = calistir([aday("gece gündüz fotosentezi", "gece gündüz, fotosentezi")] * 2)
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sayac["tekrar"], 1)


class AkisTesti(unittest.TestCase):
    def test_bozuk_cevapta_sayfa_atlanir_calisma_durmaz(self):
        mesajlar = []
        sonuc, sayac = so.uygula([], BLOKLAR + [Blok(6, 1, (0, 0, 1, 1), "Başka sayfa metni burada.", "4", "paragraf")],
                                 okuyucu=lambda baslik, metin: None if "PDF s.5" in baslik else [], ilerleme=mesajlar.append)
        self.assertEqual(sonuc, [])
        self.assertEqual((sayac["atlanan_sayfa"], sayac["okunan_sayfa"]), (1, 1))
        self.assertTrue(any("atlandı" in m for m in mesajlar))

    def test_ollama_hatasi_sayfayi_atlar(self):
        def patlayan(baslik, metin):
            raise RuntimeError("Ollama'ya bağlanılamadı")
        sonuc, sayac = so.uygula([], BLOKLAR, okuyucu=patlayan)
        self.assertEqual((sonuc, sayac["atlanan_sayfa"]), ([], 1))

    def test_bozuk_cevap_onbellege_yazilmaz(self):
        onbellek = {}
        so.uygula([], BLOKLAR, okuyucu=lambda b, m: None, onbellek=onbellek)
        self.assertEqual(onbellek, {})

    def test_onbellek_ikinci_calismada_modeli_cagirmaz(self):
        kayit, onbellek = [], {}
        adaylar = [aday("gece gündüz fotosentezi", "gece gündüz, fotosentezi")]
        ilk, _ = so.uygula([], BLOKLAR, okuyucu=okuyucu(adaylar, kayit), onbellek=onbellek)
        ikinci, sayac = so.uygula([], BLOKLAR, okuyucu=okuyucu(adaylar, kayit), onbellek=onbellek)
        self.assertEqual(len(kayit), 1)
        self.assertEqual(sayac["onbellekten"], 1)
        self.assertEqual([t.metin_parcasi for t in ilk], [t.metin_parcasi for t in ikinci])

    def test_onbellek_anahtari_sayfa_metnine_baglidir(self):
        kayit, onbellek = [], {}
        so.uygula([], BLOKLAR, okuyucu=okuyucu([], kayit), onbellek=onbellek)
        degisen = [Blok(5, 1, (0, 0, 1, 1), "Farklı metin burada yazıyor artık.", "3", "paragraf")]
        so.uygula([], degisen, okuyucu=okuyucu([], kayit), onbellek=onbellek)
        self.assertEqual(len(kayit), 2)

    def test_yalniz_secili_sayfalar_okunur(self):
        kayit = []
        so.uygula([], BLOKLAR + [Blok(6, 1, (0, 0, 1, 1), "Başka sayfa metni.", "4", "paragraf")],
                  sayfalar={6}, okuyucu=okuyucu([], kayit))
        self.assertEqual([b for b, _ in kayit], ["Kitap, PDF s.6"])

    def test_sayfa_metni_bloklari_sirayla_birlestirir(self):
        self.assertEqual(so.sayfa_metni([B1, Blok(5, 9, (0, 0, 1, 1), "  ", None, "simge"), B2]), B1.metin + "\n\n" + B2.metin)

    def test_girdi_listesi_degismez(self):
        mevcut = Tespit(5, 1, B1.bbox, "yazim", "x", 0.75, "3", "liste_tutarsiz_virgul", "gece gündüz")
        girdi = [mevcut]
        so.uygula(girdi, BLOKLAR, okuyucu=okuyucu([aday("gece gündüz fotosentezi", "gece gündüz, fotosentezi")]))
        self.assertEqual(len(girdi), 1)
        self.assertEqual(girdi[0].aciklama, "x")

    def test_uzun_sayfa_parcalara_bolunur(self):
        metin = "\n\n".join(["a" * 1500] * 4)
        parcalar = so.parcalara_bol(metin)
        self.assertEqual(len(parcalar), 2)
        self.assertEqual(len(so.parcalara_bol("kısa")), 1)

    def test_istem_ve_sema_k47_ile_ayni(self):
        self.assertTrue(so.SISTEM.startswith("Sen Türkçe ders kitapları için çalışan bir yazım editörüsün."))
        self.assertEqual(so.OZELLIKLER["hatalar"]["items"]["required"], ["kitaptaki", "onerilen", "gerekce"])
        self.assertEqual((so.MODEL, so.NUM_CTX, so.NUM_PREDICT), ("gemma4:12b-it-qat", 4096, 1024))

    def test_varsayilan_fonksiyonu(self):
        self.assertTrue(so.sayfa_okuma_varsayilani(True))
        self.assertFalse(so.sayfa_okuma_varsayilani(False))
        self.assertIsInstance(so.sayfa_okuma_varsayilani(None), bool)


class UrunMetniTesti(unittest.TestCase):
    def test_arayuz_ve_rapor_sayfa_okumayi_taniyor(self):
        from derskitabi.arayuz import ozet
        from derskitabi.rapor import TUR_ADLARI, oneri
        t = Tespit(5, 1, B1.bbox, "yazim", so._aciklama("1953’ te", "1953’te", "Boşluk olmamalı", False), 0.5, "3",
                   "sayfa_okuma", "1953’ te")
        self.assertIn("sayfa okuma", ozet.tur_adi("sayfa_okuma"))
        self.assertIn("sayfa okuma", TUR_ADLARI["sayfa_okuma"])
        self.assertEqual(oneri(t), "1953’te")
        self.assertIn("Yapay zekâ sayfayı okurken işaretledi", ozet.kisa_aciklama(t))
        self.assertIn("ölçülmüş isabeti", ozet.sade_aciklama(t))


if __name__ == "__main__":
    unittest.main()
