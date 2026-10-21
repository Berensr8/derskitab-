"""Bilgi tutarsızlığı testleri. Çalıştırma: python -m unittest -v

Gerçek modeller (Ollama) yüklenmez: konuya göre vektör veren sahte bir gömücü ve kuralla
karar veren sahte hakemler kullanılır. Modellerin gerçek başarısı mini setle ölçüldü (K18).
"""

import re
import unittest

import numpy as np

from derskitabi import yerel_model
from derskitabi.kriterler import tutarlilik
from derskitabi.kriterler.tutarlilik import aday_ciftler, analiz_et, bilgi_cumleleri, bilgi_cumlesi_mi
from derskitabi.model import Blok

KONULAR = ["malazgirt", "lübnan", "okyanus", "fok"]


def sahte_gomucu(metinler):
    """Aynı konudaki cümleler neredeyse aynı vektörü alır (benzerlik ≈ 1), farklı konular 0."""
    V = []
    for i, m in enumerate(metinler):
        v = np.zeros(len(KONULAR) + len(metinler))
        konu = next((k for k, ad in enumerate(KONULAR) if ad in m.lower()), None)
        if konu is not None:
            v[konu] = 1.0
        v[len(KONULAR) + i] = 0.1  # her cümleye küçük bir kendine özgülük
        V.append(v / np.linalg.norm(v))
    return np.array(V)


def yillar(m):
    return set(re.findall(r"\b1\d{3}\b", m))


def sahte_hakem(ikinci_gorus_katiliyor=True, hakem_aciklamada_katiliyor=True):
    cagrilar = []

    def hakem(model, a, b, aciklamali, baglam=None):
        cagrilar.append((model, aciklamali, baglam))
        celiski = bool(yillar(a)) and bool(yillar(b)) and yillar(a) != yillar(b)
        if model == tutarlilik.IKINCI_GORUS_MODELI and not ikinci_gorus_katiliyor:
            celiski = False
        if model == tutarlilik.HAKEM_MODELI and aciklamali and not hakem_aciklamada_katiliyor:
            celiski = False
        return {"karar": "celiski" if celiski else "uyumlu", "aciklama": "Yıllar farklı." if celiski else ""}
    hakem.cagrilar = cagrilar
    return hakem


def blok(sayfa, no, metin):
    return Blok(sayfa, no, (0, 0, 100, 20), metin, str(sayfa), "paragraf")


KITAP = [
    blok(20, 1, "Malazgirt Savaşı 1071 yılında Selçuklular ile Bizans arasında yapılmıştır."),
    blok(85, 2, "Selçuklular ile Bizans arasındaki Malazgirt Savaşı 1072 yılında yapılmıştır."),
    blok(40, 1, "Lübnan'ın başkenti Beyrut'tur ve Akdeniz kıyısında yer almaktadır."),
    blok(90, 3, "Akdeniz kıyısındaki Lübnan'ın başkenti olan Beyrut önemli bir limandır."),
]


class CumleSecimiTesti(unittest.TestCase):
    def test_bilgi_cumlesi(self):
        self.assertTrue(bilgi_cumlesi_mi("Malazgirt Savaşı 1071 yılında Selçuklular ile Bizans arasında yapılmıştır."))

    def test_bilgi_tasimayan_cumleler_alinmaz(self):
        for c in ["Malazgirt Savaşı hangi yılda yapılmıştır ve sonuçları nelerdir?",
                  "Hazırladığınız ürün dereceli puanlama anahtarı ile değerlendirilecektir.",
                  "Konuyla ilgili düşüncelerinizi arkadaşlarınızla tartışınız ve not alınız.",
                  "T Ü R K İ Y E K A R A D E N İ Z",
                  "Görsel 1.23 Görsel 1.24 Görsel 1.25 Görsel 1.26 Görsel 1.27",
                  "Savaş 1071 yılında yapıldı."]:  # 6 kelimeden kısa
            self.assertFalse(bilgi_cumlesi_mi(c), c)

    def test_baglam_onceki_baslik_ve_paragrafi_icerir(self):
        bloklar = [Blok(60, 1, (0, 0, 1, 1), "FİLİSTİN", "60", "kisa"),
                   blok(60, 2, "Ülkemizin güneyinde yer alan bu ülkenin resmî dili Arapçadır ve nüfusu gençtir.")]
        c = bilgi_cumleleri(bloklar)[0]
        self.assertIn("FİLİSTİN", c.baglam)
        self.assertIn("resmî dili", c.baglam)

    def test_etkinlik_yonergesi_uzakta_olsa_da_baglamda(self):
        bloklar = [blok(103, 1, "Kutulardaki bilgi doğru ise ✔ yanlış ise X ile işaretleyiniz.")] + [
            blok(103, i, f"Bu etkinlikteki {i}. ifade Türk dünyası hakkında bir bilgi vermektedir.") for i in range(2, 7)]
        self.assertIn("Etkinlik yönergesi", bilgi_cumleleri(bloklar)[-1].baglam)

    def test_test_sikki_bilgi_cumlesi_degil(self):
        self.assertFalse(bilgi_cumlesi_mi("C) Dağlar genellikle denize paralel uzanmaktadır."))

    def test_tiyatro_replikleri_karsilastirilmaz(self):
        # TDE 11, Cimri: iki replik "çelişki" sanılmıştı (K29); replikler alıntıdır, kitabın iddiası değil
        oyun = [blok(254, i, m) for i, m in enumerate(
            ["HARPAGON: Belalı şey evinde büyük para saklamak, belalı şey ve on bin altın bahçede gömülü duruyor.",
             "ÉLISE: Hayır baba, şimdi geldik ve hiçbir şey duymadık, inanın bize.",
             "HARPAGON: Ah, keşke olsa, on bin altınım olsa ve bütün dertlerim bitse!"], start=1)]
        bilgi = blok(255, 1, "Molière, Cimri oyununda insanın paraya düşkünlüğünü güldürü yoluyla eleştirir.")
        haric = tutarlilik.alinti_haric(oyun + [bilgi])  # PDF'siz: replikler metinden bulunur
        self.assertEqual({(c.sayfa_no, c.blok_no) for c in bilgi_cumleleri(oyun + [bilgi], haric)}, {(255, 1)})

    def test_roma_rakami_cumleyi_bolmez(self):
        c = bilgi_cumleleri([blok(171, 1, "Anadolu korundu. I. Haçlı Saldırısı sonucunda Haçlılar Urfa ve Kudüs gibi şehirleri ele geçirmiştir.")])
        self.assertTrue(c[-1].metin.startswith("I. Haçlı"))

    def test_karakter_konusmasi_kitabin_iddiasi_degil(self):
        konusma = blok(88, 5, "Ahmet: Enerji üretimi canlılarda ortaktır ancak tüm canlılar oksijenli solunum yapamazlar.")
        baslik = blok(88, 6, "Not: Oksijenli solunum bazı prokaryotlarda ve tüm ökaryot canlılarda gerçekleşir.")
        self.assertEqual([c.sayfa_no * 10 + c.blok_no for c in bilgi_cumleleri([konusma, baslik])], [886])

    def test_st_kisaltmasi_cumleyi_bolmez(self):
        c = bilgi_cumleleri([blok(61, 1, "Rusya Federasyonu'nun başkenti St. Petersburg değil, Moskova şehridir.")])
        self.assertIn("St. Petersburg", c[0].metin)

    def test_tekrar_eden_cumle_bir_kez(self):
        c = "Malazgirt Savaşı 1071 yılında Selçuklular ile Bizans arasında yapılmıştır."
        self.assertEqual(len(bilgi_cumleleri([blok(1, 1, c), blok(9, 1, c)])), 1)


class AdayTesti(unittest.TestCase):
    def test_ayni_konudaki_cumleler_aday(self):
        cumleler = bilgi_cumleleri(KITAP)
        ciftler = {(cumleler[i].sayfa_no, cumleler[j].sayfa_no)
                   for i, j, _ in aday_ciftler(cumleler, sahte_gomucu([c.metin for c in cumleler]))}
        self.assertEqual(ciftler, {(20, 85), (40, 90)})

    def test_ayni_bloktaki_cumleler_eslesmez(self):
        b = blok(20, 1, "Malazgirt Savaşı 1071 yılında yapılmış büyük bir savaştır. "
                        "Malazgirt Savaşı sonunda Anadolu'nun kapıları Türklere açılmıştır.")
        cumleler = bilgi_cumleleri([b])
        self.assertEqual(aday_ciftler(cumleler, sahte_gomucu([c.metin for c in cumleler])), [])

    def test_biri_digerini_iceriyorsa_eslesmez(self):
        cumleler = bilgi_cumleleri([
            blok(1, 1, "Malazgirt Savaşı 1071 yılında Selçuklular ile Bizans arasında yapılmıştır."),
            blok(5, 1, "\"...Malazgirt Savaşı 1071 yılında Selçuklular ile Bizans arasında yapılmıştır.")])
        self.assertEqual(aday_ciftler(cumleler, sahte_gomucu([c.metin for c in cumleler])), [])


class AnalizTesti(unittest.TestCase):
    def test_iki_model_hemfikirse_guven_1(self):
        tespitler = analiz_et(KITAP, sahte_gomucu, sahte_hakem())
        self.assertEqual(len(tespitler), 1)
        t = tespitler[0]
        self.assertEqual((t.kriter, t.guven_skoru, t.sayfa_no, t.ilgili_konumlar), ("tutarlilik", 1.0, 20, [(85, 2)]))
        self.assertIn("1071", t.aciklama)
        self.assertIn("1072", t.aciklama)

    def test_ikinci_gorus_tek_basina_tespit_uretmez(self):
        # K22 düzeltmesi: gemma4 açıklamalı turda "çelişki" demezse Turkish-Gemma'nın oyu yetmez
        self.assertEqual(analiz_et(KITAP, sahte_gomucu, sahte_hakem(hakem_aciklamada_katiliyor=False)), [])

    def test_kademeli_esik_birinci_komsu_daha_dusuk_benzerlikle_aday(self):
        # 0. ve 1. cümle birbirinin 1. komşusu, benzerlik 0,62: tek eşikte (0,70) elenirdi
        V = np.array([[1.0, 0.0, 0.0], [0.62, 0.785, 0.0], [0.0, 0.0, 1.0]])
        V /= np.linalg.norm(V, axis=1, keepdims=True)
        cumleler = [tutarlilik.Cumle(f"c{i}", i * 10, 1, None, (0, 0, 1, 1)) for i in range(3)]
        self.assertEqual([(i, j) for i, j, _ in aday_ciftler(cumleler, V)], [(0, 1)])

    def test_cevap_vermeyen_cift_isi_durdurmaz_ve_onbellege_yazilmaz(self):
        normal = sahte_hakem()

        def bozuk(model, a, b, aciklamali, baglam=None):
            if "Lübnan" in a:
                raise RuntimeError("Ollama hatası: llama-server terminated")
            return normal(model, a, b, aciklamali, baglam)
        onbellek = {}
        tespitler = analiz_et(KITAP, sahte_gomucu, bozuk, onbellek=onbellek)
        self.assertEqual(len(tespitler), 1)  # Malazgirt çifti yine bulundu
        self.assertFalse(any("Lübnan" in k for k in onbellek))

    def test_yalniz_biri_celiski_derse_guven_yarim(self):
        tespitler = analiz_et(KITAP, sahte_gomucu, sahte_hakem(ikinci_gorus_katiliyor=False))
        self.assertEqual([t.guven_skoru for t in tespitler], [0.5])
        self.assertIn("yalnız gemma4", tespitler[0].aciklama)

    def test_aciklamali_tur_yalniz_on_elemeden_gecenlere(self):
        hakem = sahte_hakem()
        analiz_et(KITAP, sahte_gomucu, hakem)
        hizli = [c for c in hakem.cagrilar if not c[1]]
        aciklamali = [c for c in hakem.cagrilar if c[1]]
        self.assertEqual(len(hizli), 2)  # iki aday çift
        self.assertTrue(all(c[2] is None for c in hizli))  # hızlı tur bağlamsız
        self.assertTrue(all(c[2] for c in aciklamali))  # açıklamalı tur bağlamlı
        self.assertEqual(sorted(m for m, _, _ in aciklamali),
                         sorted([tutarlilik.HAKEM_MODELI, tutarlilik.IKINCI_GORUS_MODELI]))

    def test_onbellekteki_cift_yeniden_sorulmaz(self):
        onbellek, hakem = {}, sahte_hakem()
        analiz_et(KITAP, sahte_gomucu, hakem, onbellek=onbellek)
        n = len(hakem.cagrilar)
        analiz_et(KITAP, sahte_gomucu, hakem, onbellek=onbellek)
        self.assertEqual(len(hakem.cagrilar), n)

    def test_kayit_her_adayin_kararini_tutar(self):
        kayit = []
        analiz_et(KITAP, sahte_gomucu, sahte_hakem(), kayit=kayit)
        self.assertEqual(sorted(k["hizli"] for k in kayit), ["celiski", "uyumlu"])



class YenidenDenemeTesti(unittest.TestCase):
    def test_gecici_hatada_yeniden_dener(self):
        import io
        import urllib.error
        from unittest import mock

        cevap = mock.MagicMock()
        cevap.__enter__.return_value = io.BytesIO(b'{"tamam": true}')
        hatalar = [urllib.error.URLError("connection reset"), cevap]
        with mock.patch.object(yerel_model, "YENIDEN_DENEME", (0, 0, 0)), \
             mock.patch("urllib.request.urlopen", side_effect=hatalar) as acici:
            self.assertEqual(yerel_model.istek("/api/chat", {"model": "x"}), {"tamam": True})
        self.assertEqual(acici.call_count, 2)

    def test_kalici_hata_hemen_bildirilir(self):
        import io
        import urllib.error
        from unittest import mock

        hata = urllib.error.HTTPError("u", 404, "yok", {}, io.BytesIO(b'{"error":"model not found"}'))
        with mock.patch.object(yerel_model, "YENIDEN_DENEME", (0, 0, 0)), \
             mock.patch("urllib.request.urlopen", side_effect=[hata]) as acici:
            with self.assertRaises(RuntimeError):
                yerel_model.istek("/api/chat", {"model": "x"})
        self.assertEqual(acici.call_count, 1)


if __name__ == "__main__":
    unittest.main()
