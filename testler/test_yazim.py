"""Yazım kriteri testleri. Çalıştırma: python -m unittest -v

Kural testleri gerçek morfoloji araçlarını yüklemez: "geçerli kelimeler listesi"ne bakan
sahte denetçiler kullanılır (hızlı ve araçtan bağımsız). Gerçek araçlarla tek bir
entegrasyon testi en sonda.
"""

import unittest
from collections import Counter

from derskitabi.kriterler.yazim import analiz_et, kelime_denetimi, kural_denetimi, tr_kucuk
from derskitabi.model import Blok


def blok(metin, tur="paragraf"):
    return Blok(10, 1, (0.0, 0.0, 100.0, 20.0), metin, "10", tur)


def turler(tespitler):
    return [t.alt_tur for t in tespitler]


SOZLUK = {"ali", "okula", "gitti", "ve", "kitap", "okudu", "kişisel", "gelişim", "geliyor",
          "nesil", "nesle", "nesilden", "sen", "sınıfta", "bugün"}
ikisi_de_bilir = (lambda k: k in SOZLUK, lambda k: k in SOZLUK)
yalniz_zemberek_bilir = (lambda k: k in SOZLUK, lambda k: k in SOZLUK | {"nesile"})


class KelimeDenetimiTesti(unittest.TestCase):
    def test_iki_arac_da_bilmiyorsa_guven_1(self):
        t = kelime_denetimi(blok("Ali kisisel kitap okudu."), ikisi_de_bilir)
        self.assertEqual([(x.metin_parcasi, x.guven_skoru) for x in t], [("kisisel", 1.0)])

    def test_tek_arac_bilmiyorsa_guven_yarim(self):
        t = kelime_denetimi(blok("Ali nesilden nesile kitap okudu."), yalniz_zemberek_bilir)
        self.assertEqual([(x.metin_parcasi, x.guven_skoru) for x in t], [("nesile", 0.5)])
        self.assertIn("yalnız Starlang", t[0].aciklama)

    def test_buyuk_harfle_baslayan_ozel_isim_denetlenmez(self):
        sayac = Counter()
        self.assertEqual(kelime_denetimi(blok("Ali Onega okula gitti."), ikisi_de_bilir, sayac), [])
        self.assertEqual(sayac["büyük harfle başlıyor (özel isim / başlık olabilir)"], 1)

    def test_kisaltma_kisa_parca_ve_web_adresi_atlanir(self):
        t = kelime_denetimi(blok("Ali okula gitti ve kitap okudu (vb.) zı www.ktb.gov.tr"), ikisi_de_bilir)
        self.assertEqual(t, [])

    def test_harfleri_aralikli_harita_etiketi_atlanir(self):
        self.assertEqual(kelime_denetimi(blok("YU N A N İ S TA N"), ikisi_de_bilir), [])

    def test_ek_ayrilinca_gecerliyse_aciklamada_not(self):
        t = kelime_denetimi(blok("Ali okula geliyormu sen kitap okudu."), ikisi_de_bilir)
        self.assertEqual(t[0].metin_parcasi, "geliyormu")
        self.assertIn("soru eki ayrı yazılmalı olabilir ('geliyor mu')", t[0].aciklama)


class IkinciKitapOnlemleriTesti(unittest.TestCase):
    """K15: Matematik 11 kitabında görülen sahte hata kaynakları."""

    def test_kitapta_3_kez_gecen_gecersiz_kelime_terim_sayilir(self):
        bloklar = [blok("Ali trigonometrik kitap okudu.") for _ in range(3)]
        sayac = Counter()
        self.assertEqual(analiz_et(bloklar, ikisi_de_bilir, sayac), [])
        self.assertEqual(sayac["terim: trigonometrik"], 3)

    def test_terim_sayimi_secili_sayfalarda_degil_kitabin_tamaminda(self):
        # Demo'da yalnız bazı sayfalar denetlenirken "trigonometrik" yine terim sayılmalı
        kitap = [blok("Ali trigonometrik kitap okudu.") for _ in range(3)]
        self.assertEqual(analiz_et(kitap[:1], ikisi_de_bilir, kitap_bloklari=kitap), [])
        self.assertEqual(len(analiz_et(kitap[:1], ikisi_de_bilir)), 1)

    def test_iki_kez_gecen_gecersiz_kelime_hala_hata(self):
        bloklar = [blok("Ali foksiyon kitap okudu.") for _ in range(2)]
        self.assertEqual(len(analiz_et(bloklar, ikisi_de_bilir)), 2)

    def test_harf_dusmus_blok_okuma_sorunu_sayilir(self):
        # Gerçek kitaptan (İstiklal Marşı): font "ı" harfini kaydetmemiş
        sozluk = SOZLUK | {"altındaki", "kanında", "kıymetli", "toprak"}
        denetciler = (lambda k: k in sozluk, lambda k: k in sozluk)
        sayac = Counter()
        sonuc = kelime_denetimi(blok("toprak altndaki kannda kymetli"), denetciler, sayac)
        self.assertEqual(sonuc, [])
        self.assertEqual(sayac["PDF okuma sorunu: harf düşmüş (blok)"], 1)

    def test_matematik_gosterimi_atlanir(self):
        self.assertEqual(kelime_denetimi(blok("Ali okula sinx cotx gitti."), ikisi_de_bilir), [])

    def test_gecersiz_orani_yuksek_blok_atlanir(self):
        sayac = Counter()
        metin = "Ali okula gitti kitap okudu precalculus geometry trigonometry"
        self.assertEqual(kelime_denetimi(blok(metin), ikisi_de_bilir, sayac), [])
        self.assertEqual(sayac["PDF okuma sorunu şüphesi (blok)"], 1)


class KuralTesti(unittest.TestCase):
    def test_r1_noktalamadan_sonra_bosluk(self):
        # Gerçek kitaptan: s.15
        t = kural_denetimi(blok("Roller alabiliriz.Öğrenci rolüyle bilgi ediniriz."))
        self.assertEqual(turler(t), ["noktalama_bosluk"])
        self.assertEqual(t[0].guven_skoru, 1.0)

    def test_r1_alintidaki_ucnokta_dusuk_guven(self):
        t = kural_denetimi(blok("Sanat hâline gelmiştir.(…) En sık desen çiçektir."))
        self.assertEqual(t[0].guven_skoru, 0.5)

    def test_r1_istisnalar(self):
        for metin in ["Kaynak s.230 ve vb.Diğerleri burada.", "Değişkenler x,y ve z olsun.",
                      "Oran 3,5 ve 1.5 olarak ölçüldü.", "Adres www.meb.gov.tr sayfasıdır."]:
            self.assertEqual(kural_denetimi(blok(metin)), [], metin)

    def test_r3_bag_te_ta(self):
        self.assertEqual(turler(kural_denetimi(blok("Ali kitap ta okudu bugün."))), ["bag_te_ta"])

    def test_r4_de_da_unlu_uyumu(self):
        self.assertEqual(turler(kural_denetimi(blok("Ali kitap de okudu bugün."))), ["bag_de_da_uyum"])
        self.assertEqual(kural_denetimi(blok("Ali kitap da okudu, sen de geldin.")), [])

    def test_r5_soru_eki_unlu_uyumu(self):
        t = kural_denetimi(blok("Sen bugün okula geldin mı acaba?"))
        self.assertEqual(turler(t), ["soru_eki_uyum"])
        self.assertIn("geldin mi", t[0].aciklama)
        self.assertEqual(kural_denetimi(blok("Sen bugün okula geldin mi acaba?")), [])

    def test_r6_r7_r8(self):
        self.assertEqual(turler(kural_denetimi(blok("Kalem yada kitap getir."))), ["ya_da"])
        self.assertEqual(turler(kural_denetimi(blok("Hiç bir şey olmadı."))), ["bitisik_ayri"])
        self.assertEqual(turler(kural_denetimi(blok("Herşey yolunda gitti."))), ["bitisik_ayri"])
        self.assertEqual(turler(kural_denetimi(blok("Ali ve ve Ayşe geldi."))), ["kelime_tekrari"])

    def test_buyuk_harfli_harita_etiketinde_de_da_kurali_calismaz(self):
        # Gerçek kitaptan: s.64 "ALEX AND ER TA KIMA DALA RI"
        self.assertEqual(kural_denetimi(blok("ALEX AND ER TA KIMA DALA RI")), [])

    def test_r3_r5_kisa_bloklarda_calismaz(self):
        self.assertEqual(kural_denetimi(blok("kitap ta", tur="kisa")), [])


class YardimciTesti(unittest.TestCase):
    def test_turkce_kucuk_harf(self):
        self.assertEqual(tr_kucuk("IĞDIR İZMİR"), "ığdır izmir")


class GercekAraclarTesti(unittest.TestCase):
    """Starlang ve Zemberek ile; kitapta bulunan gerçek hatalar (yükleme ~6 sn)."""

    @classmethod
    def setUpClass(cls):
        try:
            from derskitabi.kriterler.yazim import varsayilan_denetciler
            cls.denetciler = varsayilan_denetciler()
        except ImportError as e:
            raise unittest.SkipTest(f"morfoloji araçları kurulu değil: {e}")

    def test_kitaptaki_gercek_hatalar(self):
        t = analiz_et([blok("Üstlendiğimiz roller; kisisel gelisimimiz etkiler. "
                            "Değerleri nesilden nesile aktarmış.")], self.denetciler)
        bulunan = {x.metin_parcasi: x.guven_skoru for x in t}
        self.assertEqual(bulunan, {"kisisel": 1.0, "gelisimimiz": 1.0, "nesile": 0.5})

    def test_dogru_metinde_tespit_yok(self):
        t = analiz_et([blok("Hayatımızın önemli bir bölümünü oluşturan eğitim sürecinde "
                            "farklı gruplarda çeşitli roller üstleniriz.")], self.denetciler)
        self.assertEqual(t, [])


if __name__ == "__main__":
    unittest.main()
