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

    def test_tek_arac_bilmiyorsa_dusuk_oncelik(self):
        t = kelime_denetimi(blok("Ali nesilden nesile kitap okudu."), yalniz_zemberek_bilir)
        self.assertEqual([(x.metin_parcasi, x.guven_skoru) for x in t], [("nesile", 0.25)])
        self.assertIn("yalnız Starlang", t[0].aciklama)
        self.assertIn("yalnız bir araç tanımadı", t[0].aciklama)

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

    def test_terimin_ek_almis_halleri_terim_sayilir(self):
        # Biyoloji 10: "villus" tek başına sık geçiyor; "villusları" da terim
        kitap = [blok("Ali villus kitap okudu.") for _ in range(3)] + [blok("Ali villusları okudu.")]
        sayac = Counter()
        self.assertEqual(analiz_et(kitap[3:], ikisi_de_bilir, sayac, kitap_bloklari=kitap), [])
        self.assertEqual(sayac["terim: villus"], 3)

    def test_sik_tekrarlanmayan_yazim_hatasinin_ekli_hali_terim_olmaz(self):
        # Gerileme testi (Matematik 11): "foksiyon" 1 kez geçiyor; "foksiyonun" hata kalmalı
        kitap = [blok("Ali foksiyon okudu."), blok("Ali foksiyonun kitap okudu."),
                 blok("Ali foksiyonu okudu.")]
        bulunan = {t.metin_parcasi for t in analiz_et(kitap, ikisi_de_bilir)}
        self.assertEqual(bulunan, {"foksiyon", "foksiyonun", "foksiyonu"})

    def test_harf_dusmus_sayfa_duzeyinde_de_sayilir(self):
        # Biyoloji 10: İstiklal Marşı'nın her dizesi ayrı blok
        sozluk = SOZLUK | {"altındaki", "kanında", "kıymetli", "toprak"}
        denetciler = (lambda k: k in sozluk, lambda k: k in sozluk)
        dizeler = [blok(m) for m in ("toprak altndaki", "kannda toprak", "kymetli toprak")]
        self.assertEqual(analiz_et(dizeler, denetciler), [])

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
        self.assertEqual(turler(kural_denetimi(blok("Ali kitap te okudu bugün."))), ["bag_te_ta"])
        self.assertEqual(turler(kural_denetimi(blok("Ali kitap ta, defter de getirdi."))), ["bag_te_ta"])

    def test_r3_zarf_olan_ta_hata_degil(self):
        # Gerçek kitaptan (Türk Dili ve Edebiyatı 9, s.108 ve s.236)
        self.assertEqual(kural_denetimi(blok("Evet, ta Türklüğün göbeğinden, ta Uşak’tan geldik.")), [])
        self.assertEqual(kural_denetimi(blok("O hâlâ gözlerinde, ta eskiden yaptığı gibi eğlenir.")), [])

    def test_r5_tireyle_bolunmus_kelime_soru_eki_sayilmaz(self):
        # Gerçek kitaptan (TDE 9, s.119): "bunun mü-" + sonraki satır
        self.assertEqual(kural_denetimi(blok("Bir hak olduğunun inancı ve bunun mü- dafaası gerekir.")), [])

    def test_r4_de_da_unlu_uyumu(self):
        self.assertEqual(turler(kural_denetimi(blok("Ali kitap de okudu bugün."))), ["bag_de_da_uyum"])
        self.assertEqual(kural_denetimi(blok("Ali kitap da okudu, sen de geldin.")), [])

    def test_r5_soru_eki_unlu_uyumu(self):
        t = kural_denetimi(blok("Sen bugün okula geldin mı acaba?"))
        self.assertEqual(turler(t), ["soru_eki_uyum"])
        self.assertIn("geldin mi", t[0].aciklama)
        self.assertEqual(kural_denetimi(blok("Sen bugün okula geldin mi acaba?")), [])

    def test_r6_r7_r8(self):
        t = kural_denetimi(blok("Kalem yada kitap getir."))
        self.assertEqual(turler(t), ["ya_da"])
        self.assertEqual(t[0].guven_skoru, 0.5)  # türküde "yâda" (yabancıya) olabilir
        self.assertEqual(turler(kural_denetimi(blok("Hiç bir şey olmadı."))), ["bitisik_ayri"])
        self.assertEqual(turler(kural_denetimi(blok("Herşey yolunda gitti."))), ["bitisik_ayri"])
        self.assertEqual(turler(kural_denetimi(blok("Ali ve ve Ayşe geldi."))), ["kelime_tekrari"])

    def test_buyuk_harfli_harita_etiketinde_de_da_kurali_calismaz(self):
        # Gerçek kitaptan: s.64 "ALEX AND ER TA KIMA DALA RI"
        self.assertEqual(kural_denetimi(blok("ALEX AND ER TA KIMA DALA RI")), [])

    def test_r3_r5_kisa_bloklarda_calismaz(self):
        self.assertEqual(kural_denetimi(blok("kitap ta", tur="kisa")), [])

    def test_r13_parantez_cift_nokta(self):
        t = kural_denetimi(blok("Molekül asimetrik yapı kazanır. (Görsel 1.26). Bu yapı önemlidir."))
        self.assertEqual([x.alt_tur for x in t], ["noktalama_parantez_cift_nokta"])
        self.assertEqual(t[0].guven_skoru, 1.0)

    def test_r14_cift_tek_tirnak(self):
        t = kural_denetimi(blok("Analitik Dereceli ‘‘Puanlama Anahtarı’’ ile değerlendiriniz."))
        self.assertEqual([x.alt_tur for x in t], ["noktalama_cift_tek_tirnak", "noktalama_cift_tek_tirnak"])
        self.assertEqual(t[0].guven_skoru, 0.25)
        self.assertIn("basılı sayfada görünmez", t[0].aciklama)

    def test_r15_ters_acilis_tirnagi(self):
        t = kural_denetimi(blok("Bir atlı geldi. ”Yüce dağların başında” türküsünü söyledi."))
        self.assertIn("noktalama_ters_tirnak", [x.alt_tur for x in t])
        self.assertEqual(t[0].guven_skoru, 0.25)
        self.assertIn("basılı sayfada görünmeyebilir", t[0].aciklama)

    def test_r16_dizgi_rakam_harf(self):
        t1 = kural_denetimi(blok("NİN HAYATI (…) 0 civar karyelerinden birinde doğdu."))
        self.assertEqual([x.alt_tur for x in t1], ["dizgi_rakam_harf"])
        self.assertEqual(t1[0].metin_parcasi, "0 civar")
        self.assertEqual(t1[0].guven_skoru, 0.5)

        t2 = kural_denetimi(blok("Köylüler c0var tepelerini aştılar."))
        self.assertEqual([x.alt_tur for x in t2], ["dizgi_rakam_harf"])
        self.assertEqual(t2[0].metin_parcasi, "c0var")

        # Ölçü birimleri, formüller ve puan ifadeleri atlanır
        self.assertEqual(kural_denetimi(blok("I. Grup: 0 puan aldı.")), [])
        self.assertEqual(kural_denetimi(blok("Bugün hava 0 derece.")), [])
        self.assertEqual(kural_denetimi(blok("Formül H2O olup 30kg ve 10 km yol aldı.")), [])
        self.assertEqual(kural_denetimi(blok("Büyütme 40x olarak ayarlandı.")), [])


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
        self.assertEqual(bulunan, {"kisisel": 1.0, "gelisimimiz": 1.0, "nesile": 0.25})

    def test_dogru_metinde_tespit_yok(self):
        t = analiz_et([blok("Hayatımızın önemli bir bölümünü oluşturan eğitim sürecinde "
                            "farklı gruplarda çeşitli roller üstleniriz.")], self.denetciler)
        self.assertEqual(t, [])

    def test_yumusama_ve_ikizlesme_sirasi_sabit(self):
        # "tıp" kökü: önce yumuşama (p→b), sonra ikizleşme (bb). Sıra hash tohumuna bağlıyken
        # bu kelimeler bazı çalıştırmalarda geçersiz sayılıyordu (zemberek_kok_sirasini_sabitle).
        zemberek = self.denetciler[1]
        for kelime in ("tıbba", "tıbbın", "hakka", "hakkın"):
            self.assertTrue(zemberek(kelime), kelime)

    def test_ozellikler_tanim_sirasiyla_dolasilir(self):
        from zemberek.core.turkish import RootAttribute
        from derskitabi.kriterler.yazim import _TanimSirasiylaKume
        kume = _TanimSirasiylaKume({RootAttribute.Doubling, RootAttribute.Voicing})
        self.assertEqual(list(kume), [RootAttribute.Voicing, RootAttribute.Doubling])


class BuyukHarfITesti(unittest.TestCase):
    def test_buyuk_harfli_baslikta_i_noktali_karismasi(self):
        from derskitabi.kriterler.yazim import buyuk_harf_i_denetimi
        sozluk = {"zararlı", "veya", "tahriş", "edici", "madde", "ısıtıcı"}
        sahte_arac = (lambda k: k in sozluk, lambda k: k in sozluk)
        b = blok("ZARARLI VEYA TAHRIŞ EDICI MADDE")
        t = buyuk_harf_i_denetimi(b, sahte_arac)
        self.assertEqual([x.metin_parcasi for x in t], ["TAHRIŞ", "EDICI"])
        self.assertEqual(t[0].alt_tur, "buyuk_harf_i")
        self.assertEqual(t[0].guven_skoru, 0.5)

    def test_gecerli_ve_kisa_buyuk_harfli_kelimeler_atlanir(self):
        from derskitabi.kriterler.yazim import buyuk_harf_i_denetimi
        sozluk = {"ısıtıcı", "ve", "soğutucu"}
        sahte_arac = (lambda k: k in sozluk, lambda k: k in sozluk)
        b = blok("ISITICI VE SOĞUTUCU DNA ATP")
        t = buyuk_harf_i_denetimi(b, sahte_arac)
        self.assertEqual(t, [])


class NispetDuzeltmeIsaretiTesti(unittest.TestCase):
    def test_nispet_i_tek_tespit_ve_sayim(self):
        from derskitabi.kriterler.yazim import nispet_i_denetimi
        b1 = blok("MİLLİ EDEBİYAT DÖNEMİ", tur="kisa")
        b2 = blok("Milli Edebiyat akımı ve milli marşımız üzerine çalıştı.", tur="paragraf")
        t = nispet_i_denetimi([b1, b2])
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0].alt_tur, "duzeltme_isareti_nispet")
        self.assertEqual(t[0].guven_skoru, 0.5)
        self.assertEqual(t[0].metin_parcasi, "MİLLİ")
        self.assertIn("MİLLÎ", t[0].aciklama)
        self.assertIn("3 kez geçiyor", t[0].aciklama)

    def test_kucuk_harfli_milli(self):
        from derskitabi.kriterler.yazim import nispet_i_denetimi
        b = blok("Bu bir milli meseledir.")
        t = nispet_i_denetimi([b])
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0].metin_parcasi, "milli")
        self.assertIn("millî", t[0].aciklama)
        self.assertNotIn("kez geçiyor", t[0].aciklama)


if __name__ == "__main__":
    unittest.main()
