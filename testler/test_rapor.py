"""Excel raporu testleri (K27). Çalıştırma: python -m unittest -v"""

import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from derskitabi.model import Blok, Tespit
from derskitabi.rapor import (HARF, KARARLAR, SUTUN, editor_kararlari, isabet_ozeti, kimlik, oneri,
                              rapor_olustur, tespit_satirlari)
from derskitabi.sonuclar import KitapSonuclari

B1 = Blok(3, 1, (50, 100, 300, 140), "Cumhuriyet 1923 yılında ilan edildi. Bu bir denme cümlesidir.", "1")
B2 = Blok(5, 2, (50, 200, 300, 240), "Cumhuriyet 1920 yılında ilan edildi.", "3")


def _sonuclar(tutarlilik=True):
    yazim = [
        Tespit(5, 2, B2.bbox, "yazim", "x. Önerilen yazım: 'deneme'.", 0.75, "3", "morfoloji", "denme"),
        Tespit(3, 1, B1.bbox, "yazim", "y", 0.25, "1", "morfoloji", "Cumhuriyet"),
        Tespit(3, 1, B1.bbox, "yazim", "z", 1.0, "1", "noktalama_bosluk", "edildi.Bu"),
    ]
    oku = [Tespit(3, 1, B1.bbox, "okunabilirlik", "zor", 0.67, "1", "kitap_ici_zor_paragraf", "uzun cümle")]
    a = "Cumhuriyet 1923 yılında ilan edildi."
    tut = [Tespit(3, 1, B1.bbox, "tutarlilik", "çelişki", 1.0, "1", "kitap_ici_celiski", a, [(5, 2)])]
    kayit = [{"a": {"metin": a, "sayfa_no": 3, "blok_no": 1}, "b": {"metin": B2.metin, "sayfa_no": 5, "blok_no": 2}}]
    return KitapSonuclari([B1, B2], {"yazim": yazim, "okunabilirlik": oku,
                                     "tutarlilik": tut if tutarlilik else None}, None, kayit)


class SatirTesti(unittest.TestCase):
    def test_satirlar_kitap_sirasinda_ve_alanlar(self):
        s = tespit_satirlari(_sonuclar())
        self.assertEqual([x["No"] for x in s], [1, 2, 3, 4, 5])
        self.assertEqual([x["PDF s."] for x in s], [3, 3, 3, 3, 5])
        son = s[-1]
        self.assertEqual((son["Öneri"], son["Öncelik"], son["Tür"]), ("deneme", "yüksek", "kelime (yazım)"))
        celiski = next(x for x in s if x["Kriter"] == "Bilgi tutarsızlığı")
        self.assertIn("PDF s. 5 / kitap s. 3", celiski["Karşı cümle (tutarlılık)"])
        self.assertIn("1920", celiski["Karşı cümle (tutarlılık)"])
        self.assertEqual({x["Öncelik"] for x in s if x["İlgili metin"] == "Cumhuriyet"}, {"düşük"})

    def test_oneri_yalniz_hakemden(self):
        self.assertEqual(oneri(_sonuclar().tespitler["yazim"][1]), "")


class RaporDosyasiTesti(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.TemporaryDirectory()
        self.yol = Path(self.klasor.name) / "rapor.xlsx"

    def tearDown(self):
        self.klasor.cleanup()

    def test_sayfalar_bicim_ve_dogrulama(self):
        sayilar = rapor_olustur(self.yol, _sonuclar(), "ornek.pdf", 10)
        self.assertEqual(sayilar["Yazım ve dil"], 3)
        wb = load_workbook(self.yol)
        self.assertEqual(wb.sheetnames, ["Özet", "Tespitler"])
        ws = wb["Tespitler"]
        self.assertEqual(ws.max_row, 6)
        self.assertEqual(ws.freeze_panes, "A2")
        self.assertEqual(ws.auto_filter.ref, f"A1:{HARF['Kimlik']}6")
        dv = ws.data_validations.dataValidation[0]
        self.assertEqual(str(dv.sqref), f"{HARF['Editör kararı']}2:{HARF['Editör kararı']}6")
        self.assertEqual(dv.formula1, '"Hata,Hata değil,Emin değilim"')
        self.assertTrue(ws.column_dimensions[HARF["Kimlik"]].hidden)
        self.assertEqual(ws.cell(row=2, column=1).font.name, "Arial")

    def test_ozet_formulleri_dogru_sutunlara_bakar(self):
        rapor_olustur(self.yol, _sonuclar(), "ornek.pdf")
        oz = load_workbook(self.yol)["Özet"]
        formuller = [c.value for r in oz.iter_rows() for c in r if isinstance(c.value, str) and c.value.startswith("=")]
        k, o, e = (f"Tespitler!${HARF[a]}:${HARF[a]}" for a in ("Kriter", "Öncelik", "Editör kararı"))
        self.assertTrue(any(f.startswith(f"=COUNTIFS({k},$A") and f.endswith(f'{o},"yüksek")') for f in formuller))
        self.assertTrue(any(f.endswith(f'{e},"Hata değil")') for f in formuller))
        self.assertTrue(any(f.startswith("=IFERROR(") for f in formuller))

    def test_calistirilmayan_kriter_yazilir(self):
        rapor_olustur(self.yol, _sonuclar(tutarlilik=False), "ornek.pdf")
        oz = load_workbook(self.yol)["Özet"]
        degerler = [c.value for r in oz.iter_rows() for c in r]
        self.assertIn("çalıştırılmadı", degerler)

    def test_editor_kararlari_geri_okunur(self):
        rapor_olustur(self.yol, _sonuclar(), "ornek.pdf")
        wb = load_workbook(self.yol)
        ws = wb["Tespitler"]
        kararlar = {"denme": "Hata", "Cumhuriyet": "Hata değil", "edildi.Bu": "Hata"}
        for r in range(2, ws.max_row + 1):
            metin = ws.cell(row=r, column=SUTUN["İlgili metin"]).value
            if metin in kararlar:
                ws.cell(row=r, column=SUTUN["Editör kararı"], value=kararlar[metin])
        ws.cell(row=2, column=SUTUN["Editör notu"], value="deneme notu")
        ws.move_range(f"A2:{HARF['Kimlik']}3", rows=10)  # editör satırların yerini değiştirse de
        wb.save(self.yol)
        okunan = editor_kararlari(self.yol)
        self.assertEqual(len(okunan), 5)
        self.assertIn(kimlik(_sonuclar().tespitler["yazim"][0]), {k["kimlik"] for k in okunan})
        ozet = isabet_ozeti(okunan)
        self.assertEqual(ozet["Yazım ve dil"]["Hata"], 2)
        self.assertAlmostEqual(ozet["Yazım ve dil"]["isabet"], 2 / 3)
        self.assertIsNone(ozet["Bilgi tutarsızlığı"]["isabet"])  # bakılmadı
        self.assertEqual(ozet["Bilgi tutarsızlığı"]["Bakılmadı"], 1)

    def test_listede_olmayan_karar_sayilmaz(self):
        rapor_olustur(self.yol, _sonuclar(), "ornek.pdf")
        wb = load_workbook(self.yol)
        wb["Tespitler"].cell(row=2, column=SUTUN["Editör kararı"], value="belki")
        wb.save(self.yol)
        self.assertNotIn("belki", {k["karar"] for k in editor_kararlari(self.yol)})
        self.assertEqual(KARARLAR, ("Hata", "Hata değil", "Emin değilim"))


if __name__ == "__main__":
    unittest.main()
