"""Arayüz testleri: sonuç ekranı cümleleri, geçmiş kaydı, sunucu (gerçek analiz çalıştırılmaz)."""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from derskitabi.arayuz import gecmis, ozet, sunucu
from derskitabi.model import Blok, Tespit


def tespit(sayfa, guven, alt_tur="morfoloji", parca="kisisel", kriter="yazim", aciklama="'kisisel' kelimesi çözümlenemedi."):
    return Tespit(sayfa_no=sayfa, blok_no=1, bbox=(1, 1, 2, 2), kriter=kriter, aciklama=aciklama,
                  guven_skoru=guven, basili_sayfa_no=str(sayfa - 2), alt_tur=alt_tur, metin_parcasi=parca)


BLOKLAR = {(s, 1): Blok(s, 1, (1, 1, 2, 2), "Üstlendiğimiz roller kisisel gelişimimizi etkiler ve "
                                          "sorumluluklarımızı artırır.", str(s - 2), "paragraf") for s in range(1, 30)}


class OzetTesti(unittest.TestCase):
    def test_yazim_cumleleri_ve_sayilar(self):
        t = [tespit(5, 1.0), tespit(6, 1.0), tespit(7, 0.5, "ozel_ad_kesme", "Tibete"), tespit(8, 0.25)]
        o = ozet.kriter_ozeti("yazim", t, BLOKLAR, hakem=False)
        self.assertEqual(o["sayilar"], {"yüksek": 2, "orta": 1, "düşük": 1})
        self.assertEqual(o["cumleler"][0], "Yazımda 3 olası hata var. Önce bakılması gerekenler: 2.")
        self.assertEqual(o["cumleler"][1], "Türlerine göre: kelime yazımı (2), özel ada gelen ekte kesme eksik (1).")
        self.assertIn("1 yer daha var ama büyük ihtimalle hata değil", o["cumleler"][2])
        self.assertEqual(ozet.kriter_ozeti("yazim", t[:2], BLOKLAR)["cumleler"][1], "Hepsi kelime yazımı türünde.")
        self.assertIn("hakemi kapalıydı", o["guven"])  # hakem çalışmadıysa söylenir
        self.assertNotIn("hakemi kapalıydı", ozet.kriter_ozeti("yazim", t, BLOKLAR, hakem=True)["guven"])
        # örnekler: farklı türlerden, düşük öncelik yok
        ornekler = [m for m in o["maddeler"] if m["no"] in o["ornekler"]]
        self.assertEqual({m["tur"] for m in ornekler}, {"kelime yazımı", "özel ada gelen ekte kesme eksik"})
        self.assertNotIn("düşük", {m["oncelik"] for m in ornekler})

    def test_hata_olmayanlara_oncelik_verilmez(self):
        # zor paragraf ve müfredat notu hata değildir: "öncelikli" sayılmaz (arayüz incelemesi, 2026-11-05)
        t = Tespit(sayfa_no=5, blok_no=1, bbox=(1, 1, 2, 2), kriter="okunabilirlik", guven_skoru=1.0,
                   alt_tur="kitap_ici_zor_paragraf", aciklama="Bu paragraf, 3 formülden 3 tanesine göre kitabın en zor "
                   "%10'luk diliminde. Ateşman 18.6 (çok zor), Çetinkaya-Uzun 8.5 (engelli okuma düzeyi (10–12. sınıf)). "
                   "Cümle başına ortalama 23.0 kelime (kitap ortancası 10.0), kelime başına 3.92 hece.")
        o = ozet.kriter_ozeti("okunabilirlik", [t], BLOKLAR)
        self.assertEqual((o["sayilar"], o["oncelikli"], o["maddeler"][0]["oncelik"]), ({}, False, None))
        self.assertEqual(o["maddeler"][0]["kisa"], "Cümleler uzun: ortalama 23 kelime (kitapta genelde 10).")
        self.assertNotIn("engelli", o["maddeler"][0]["sade"])
        self.assertIn("10–12. sınıf düzeyinde", o["maddeler"][0]["sade"])

    def test_noktalama_vurgusu_kelimeyi_bolmez(self):
        t = tespit(5, 1.0, "noktalama_bosluk", "ikiye katlandı.Takım arkada")
        self.assertEqual(ozet.madde(t, 1, BLOKLAR)["parca"], "katlandı.Takım")

    def test_celiskide_karsi_cumle_gosterilir(self):
        t = Tespit(sayfa_no=242, blok_no=1, bbox=(1, 1, 2, 2), kriter="tutarlilik", guven_skoru=0.5,
                   metin_parcasi="Söylevin amacı duyguları harekete geçirmektir.",
                   aciklama='s. 241: "Söylevin amacı duyguları harekete geçirmektir." ile s. 256: "Söylevin amacı bilgi '
                            'vermektir." çelişiyor olabilir (yalnız gemma4). Açıklama.')
        self.assertEqual(ozet.kisa_aciklama(t), "Şu bilgiyle çelişiyor olabilir (s. 256): “Söylevin amacı bilgi vermektir.”")
        self.assertIn("yapay zekâ modellerinden biri", ozet.sade_aciklama(t))

    def test_hic_hata_yoksa(self):
        self.assertEqual(ozet.kriter_ozeti("yazim", [], BLOKLAR)["cumleler"], ["Yazımda hata bulunmadı."])
        self.assertIn("hepsi", ozet.kriter_ozeti("mufredat", [], BLOKLAR)["cumleler"][0])

    def test_calismayan_kriter(self):
        o = ozet.kriter_ozeti("tutarlilik", None, BLOKLAR, neden="Yerel model kapalı.")
        self.assertEqual((o["durum"], o["neden"]), ("atlandı", "Yerel model kapalı."))

    def test_alinti_parcayi_ortalar_ve_kelime_bolmez(self):
        m = ozet.madde(tespit(5, 1.0), 1, BLOKLAR)
        a = m["alinti"]
        self.assertEqual(a["vurgu"], "kisisel")
        self.assertTrue(a["once"].endswith("roller "))
        self.assertEqual(m["sayfa"], 5)
        self.assertEqual(m["basili"], "3")

    def test_konumsuz_tespit_baglantisiz(self):
        t = Tespit(sayfa_no=1, blok_no=0, bbox=(0, 0, 0, 0), kriter="mufredat", aciklama="Kavram 'x' geçmiyor.",
                   guven_skoru=1.0, alt_tur="kavram_yok", metin_parcasi="polimerizasyon")
        o = ozet.kriter_ozeti("mufredat", [t], BLOKLAR)
        self.assertIsNone(o["maddeler"][0]["sayfa"])
        self.assertIn("polimerizasyon", o["cumleler"][0])

    def test_hakem_onerisi_kisa_aciklamada(self):
        t = tespit(5, 1.0, aciklama="'kisisel' kelimesi çözümlenemedi (iki araç da: Starlang ve Zemberek). "
                                    "Dil modeli (gemma4) de yazım hatası dedi. Önerilen yazım: 'kişisel'.")
        self.assertIn("önerilen: kişisel", ozet.kisa_aciklama(t))
        sade = ozet.sade_aciklama(t)
        self.assertNotIn("Starlang", sade)
        self.assertIn("hakemi de hata dedi", sade)


class GecmisTesti(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.eski = gecmis.GECMIS
        gecmis.GECMIS = Path(self.gecici.name)

    def tearDown(self):
        gecmis.GECMIS = self.eski
        self.gecici.cleanup()

    def test_kaydet_listele_sil(self):
        a = gecmis.yeni({"pdf": "D:/a/biyoloji9.pdf", "cikti": "D:/x", "kitap_adi": "Biyoloji 9"})
        b = gecmis.yeni({"pdf": "D:/a/kitap.pdf", "cikti": "D:/y"})
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual([k["kitap_adi"] for k in gecmis.listele()][::-1], ["Biyoloji 9", "kitap"])
        self.assertEqual(gecmis.oku(a["id"])["kullanici"], "yerel")
        gecmis.sil(a["id"])
        self.assertIsNone(gecmis.oku(a["id"]))

    def test_gecersiz_kimlik(self):
        with self.assertRaises(ValueError):
            gecmis.oku("../ayar")


class SunucuTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gecici = tempfile.TemporaryDirectory()
        cls.eski = gecmis.GECMIS
        gecmis.GECMIS = Path(cls.gecici.name) / "gecmis"
        cls.cikti = Path(cls.gecici.name) / "cikti"
        cls.cikti.mkdir()
        (cls.cikti / "inceleme.html").write_text("<p>merhaba</p>", encoding="utf-8")
        (cls.cikti / "ozet.json").write_text(json.dumps({"kriterler": {}, "sure_sn": 3}), encoding="utf-8")
        (cls.cikti / "ilerleme.jsonl").write_text(json.dumps({"durum": "tamam"}) + "\n", encoding="utf-8")
        cls.kayit = gecmis.yeni({"pdf": "D:/a/kitap.pdf", "cikti": str(cls.cikti)})
        cls.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), sunucu.Isleyici)
        cls.adres = f"http://127.0.0.1:{cls.sunucu.server_address[1]}"
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()
        gecmis.GECMIS = cls.eski
        cls.gecici.cleanup()

    def _al(self, yol, govde=None, basliklar=None):
        istek = urllib.request.Request(self.adres + yol, data=None if govde is None else json.dumps(govde).encode(),
                                       headers={"Content-Type": "application/json", **(basliklar or {})})
        try:
            with urllib.request.urlopen(istek, timeout=5) as y:
                return y.status, y.read()
        except urllib.error.HTTPError as h:
            return h.code, h.read()

    def test_ana_sayfa(self):
        kod, govde = self._al("/")
        self.assertEqual(kod, 200)
        self.assertIn("Ders Kitabı".encode(), govde)

    def test_biten_inceleme_ozetle_doner(self):
        kod, govde = self._al(f"/api/inceleme/{self.kayit['id']}")
        veri = json.loads(govde)
        self.assertEqual((kod, veri["kayit"]["durum"]), (200, "bitti"))
        self.assertEqual(veri["ozet"]["sure_sn"], 3)

    def test_cikti_dosyasi_ve_klasor_disina_cikilamaz(self):
        self.assertEqual(self._al(f"/cikti/{self.kayit['id']}/inceleme.html")[0], 200)
        self.assertEqual(self._al(f"/cikti/{self.kayit['id']}/..%2F..%2Fgizli.txt")[0], 404)

    def test_baska_siteden_istek_reddedilir(self):
        kod, _ = self._al(f"/api/inceleme/{self.kayit['id']}/sil", {}, {"Origin": "https://kotu.example"})
        self.assertEqual(kod, 403)
        self.assertIsNotNone(gecmis.oku(self.kayit["id"]))


if __name__ == "__main__":
    unittest.main()
