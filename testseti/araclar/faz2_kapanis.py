"""Faz 2 kapanış ölçümü: bütün kitaplarda yazım tespitlerinin Faz 1 → Faz 2 değişimi ve etiketli
örneklemlerde son sistemin isabeti.

Son sistem = yazım kriteri + kitap ipuçları (K28 alıntı, K29 PDF parçası/terim) + yazım hakemi (K25).
Hakem cevapları önbellekten okunur (önce: python -m derskitabi.kriterler.yazim veri/<kitap>_bloklar.json --hakem);
önbellekte olmayan kelime hakeme sorulmamış sayılır (tespit olduğu gibi kalır).
Etiketler: K23 (Sosyal 6, Biyoloji 10), K25 (Matematik 11, TDE 9), K29 körlemesine (Biyoloji 9, Biyoloji 11, TDE 12).
Not: K23/K25 etiketleri ve K29 testi Faz 2 geliştirmesinde görüldü; bu tablo özet içindir, temiz test değildir.
Kullanım: python testseti/araclar/faz2_kapanis.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJE))
from derskitabi.kayit import bloklari_yukle  # noqa: E402
from derskitabi.kriterler import dusuk_oncelik, okunabilirlik, yazim, yazim_hakem  # noqa: E402
from derskitabi.model import Tespit  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
KITAPLAR = ["kitap", "biyoloji9", "biyoloji10", "biyoloji11", "matematik11",
            "turkdili9", "turkdili10", "turkdili11", "turkdili12"]
ADLAR = {"kitap": "Sosyal Bilgiler 6", "biyoloji9": "Biyoloji 9", "biyoloji10": "Biyoloji 10",
         "biyoloji11": "Biyoloji 11", "matematik11": "Matematik 11", "turkdili9": "TDE 9",
         "turkdili10": "TDE 10", "turkdili11": "TDE 11", "turkdili12": "TDE 12"}
ETIKETLER = {"K23": "yazim_etiketler.json", "K25": "yazim_etiketler_test.json", "K29": "yazim_etiketler_k29.json"}
ONBELLEK = json.loads((PROJE / "veri" / "yazim_hakem_onbellek.json").read_text(encoding="utf-8"))
DENETCILER = yazim.varsayilan_denetciler()


def _sorulmadi(*_):
    raise RuntimeError("önbellekte yok")


def son_sistem(kitap: str, bloklar, tespitler: list[Tespit]) -> list[Tespit]:
    t = dusuk_oncelik.isaretle(PROJE / "veri" / f"{kitap}.pdf", bloklar, tespitler, DENETCILER)
    return yazim_hakem.hakemle(t, bloklar, hakem=_sorulmadi, onbellek=ONBELLEK, kitap_bloklari=bloklar,
                               denetciler=DENETCILER)


def sebep(t: Tespit) -> str:
    if t.guven_skoru >= 0.5:
        return "gösterilir"
    return dusuk_oncelik.sebep(t) or ("hakem: muhtemelen doğru" if "muhtemelen doğru" in t.aciklama else "diğer")


satirlar, ozet = [], {}
for kitap in KITAPLAR:
    bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
    ham = yazim.analiz_et(bloklar, DENETCILER)
    son = son_sistem(kitap, bloklar, ham)
    c = Counter(map(sebep, son))
    try:
        okun = len(okunabilirlik.analiz_et(bloklar)[1])
    except ValueError:
        okun = 0
    tut_yolu = PROJE / "veri" / f"{kitap}_tutarlilik_tespitler.json"
    tut = len(json.loads(tut_yolu.read_text(encoding="utf-8"))) if tut_yolu.exists() else None
    ozet[kitap] = {"yazim_tespit": len(ham), "faz1_gosterilen": sum(t.guven_skoru >= 0.5 for t in ham),
                   "faz2_gosterilen": c["gösterilir"], "dusuren": {k: v for k, v in c.items() if k != "gösterilir"},
                   "okunabilirlik": okun, "tutarlilik": tut}
    print(ADLAR[kitap], ozet[kitap], flush=True)

print("\nEtiketli örneklemlerde son sistem:")
isabet = {}
for set_adi, dosya in ETIKETLER.items():
    etiketler = json.loads((PROJE / "testseti" / dosya).read_text(encoding="utf-8"))
    for kitap in sorted({x["kitap"] for x in etiketler}):
        e = [x for x in etiketler if x["kitap"] == kitap]
        bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        ts = son_sistem(kitap, bloklar, [Tespit(x["sayfa_no"], x["blok_no"], (0, 0, 1, 1), "yazim", "", x["guven"],
                                               alt_tur=x["alt_tur"], metin_parcasi=x["parca"]) for x in e])
        gos = [(x, t) for x, t in zip(e, ts) if t.guven_skoru >= 0.5 and x["etiket"] != "belirsiz"]
        once = [x for x in e if x["guven"] >= 0.5 and x["etiket"] != "belirsiz"]
        g_once = sum(x["etiket"] == "gercek" for x in once)
        g_son = sum(x["etiket"] == "gercek" for x, _ in gos)
        isabet[f"{set_adi} {kitap}"] = {
            "once": f"{g_once}/{len(once)}", "precision_once": round(g_once / len(once), 3) if once else None,
            "son": f"{g_son}/{len(gos)}", "precision_son": round(g_son / len(gos), 3) if gos else None,
            "kaybolan_gercek": [x["parca"] for x, t in zip(e, ts) if x["etiket"] == "gercek" and t.guven_skoru < 0.5]}
        print(f"  {set_adi} {ADLAR[kitap]:18}", isabet[f"{set_adi} {kitap}"], flush=True)

(PROJE / "veri" / "faz2_kapanis.json").write_text(json.dumps({"kitaplar": ozet, "isabet": isabet}, ensure_ascii=False,
                                                              indent=1), encoding="utf-8")
