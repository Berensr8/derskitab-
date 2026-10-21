"""Değerlendirme: tutarlılık kriterini bilerek eklenmiş çelişkilerle ölçer (K20).

Kilitli test setindeki çelişkiler blok dosyasının bir kopyasına uygulanır (PDF'e dokunulmaz),
tutarlılık kriteri çalıştırılır ve her çelişkinin hangi aşamada bulunduğu ya da kaybolduğu
raporlanır:
  cümle   : eklenen/değiştirilen cümle ve kaynağı "bilgi cümlesi" olarak seçildi mi
  aday    : ikisi aday çift oldu mu (bge-m3 benzerliği, K21)
  hızlı   : gemma4'ün hızlı turu "çelişki" dedi mi
  tespit  : son tespit oldu mu (güven 0,5 ya da 1,0; K22)

Kural (K20): ayar yaparken yalnız geliştirme maddeleri eklenir ve ölçülür; test maddeleri
yalnız en sonda bir kez (--set test).

Kullanım:
    python -m derskitabi.degerlendirme --set gelistirme
"""

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from .kayit import bloklari_yukle, json_kaydet
from .kriterler import tutarlilik
from .model import Blok

PROJE = Path(__file__).resolve().parents[1]
SET_YOLU = PROJE / "testseti" / "tutarlilik_celiskileri.json"
KILIT_SHA256 = "740101f40e2a0ea78e2acbae78bb069ba65e8d8057c22a8f9a4a8469fa300df0"  # K20 eki
KITAPLAR = {"kitap": PROJE / "veri" / "kitap_bloklar.json", "biyoloji10": PROJE / "veri" / "biyoloji10_bloklar.json"}
ASAMALAR = ("cumle", "aday", "hizli", "tespit")


def test_modu_kaydi_yolu(kitap: str, set_adi: str) -> Path:
    return PROJE / "veri" / f"{kitap}_degerlendirme_{set_adi}_adaylar.json"


def set_yukle(yol: Path = SET_YOLU, kilit: str | None = KILIT_SHA256) -> list[dict]:
    veri = Path(yol).read_bytes()
    if kilit and hashlib.sha256(veri).hexdigest() != kilit:
        raise ValueError(f"{yol} kilitlendikten sonra değişmiş (SHA-256 uyuşmuyor). Test seti değiştirilmemeli.")
    return json.loads(veri.decode("utf-8"))


def celiskileri_uygula(bloklar: list[Blok], ogeler: list[dict]) -> list[Blok]:
    """Blokların kopyasına maddeleri uygular: 'degistir' metindeki ifadeyi değiştirir,
    'ekle' cümleyi paragrafın sonuna ekler."""
    yeni = copy.deepcopy(bloklar)
    dizin = {(b.sayfa_no, b.blok_no): b for b in yeni}
    for o in ogeler:
        h = o["hedef"]
        b = dizin[(h["sayfa_no"], h["blok_no"])]
        if h["islem"] == "degistir":
            if b.metin.count(h["eski"]) != 1:
                raise ValueError(f"{o['id']}: değiştirilecek ifade blokta tam bir kez geçmiyor")
            b.metin = b.metin.replace(h["eski"], h["yeni"])
        else:
            b.metin = b.metin.rstrip() + ("" if b.metin.rstrip()[-1:] in ".!?…\"”" else ".") + " " + h["yeni"]
    return yeni


def eklenen_mi(oge: dict, cumle: str) -> bool:
    """Cümle bu maddenin eklenen (yanlış) ifadesini taşıyor mu? Cümle bölücü eklenen cümleyi
    bölebilir ("Hz. Muhammed'in…" → "Muhammed'in…", test koşusunda görüldü): bu yüzden cümlenin
    eklenen ifadenin uzun bir parçası olması da yeterli."""
    eklenen = oge["hedef"]["yeni"]
    return eklenen in cumle or (len(cumle) >= 25 and cumle in eklenen)


def eslesir(oge: dict, a: str, b: str) -> bool:
    """(a, b) cümle çifti bu maddenin çelişkisi mi: bir taraf eklenen ifadeyi, diğeri kaynaklardan
    birini içeriyor."""
    kaynak = [k["parca"] for k in oge["kaynaklar"]]
    return any(eklenen_mi(oge, x) and any(p in y for p in kaynak) for x, y in ((a, b), (b, a)))


def _iceriyor(oge: dict, k: dict) -> bool:
    """Aday çiftin bir tarafı bu maddenin eklenen (yanlış) ifadesi mi?"""
    return eklenen_mi(oge, k["a"]["metin"]) or eklenen_mi(oge, k["b"]["metin"])


def puanla(ogeler: list[dict], cumleler: list[str], kayit: list[dict]) -> dict:
    """Her maddenin ulaştığı son aşama + eklenmemiş (fazladan) tespitler.

    Eklenen yanlış cümle bir tespitte yer alıyorsa madde bulunmuş sayılır — karşı taraf bizim
    yazdığımız kaynak cümle olmasa da (geliştirme setinde görüldü: "bir kez Krebs" kitabın başka
    bir cümlesiyle de gerçekten çelişiyor). Karşı tarafın kaynak olup olmadığı ayrıca kaydedilir.
    Aday aşaması ise kaynakla eşleşmeye bakar (aday bulmanın asıl ölçüsü).
    """
    sonuc = {}
    for o in ogeler:
        eklenen_var = any(eklenen_mi(o, c) for c in cumleler)
        kaynak_var = any(k["parca"] in c for k in o["kaynaklar"] for c in cumleler)
        ilgili = [k for k in kayit if _iceriyor(o, k)]
        kaynakli = [k for k in ilgili if eslesir(o, k["a"]["metin"], k["b"]["metin"])]
        tespitler = [k for k in ilgili if k.get("guven")]
        guven = max((k["guven"] for k in tespitler), default=0)
        asama = ("tespit" if tespitler else "hizli" if any(k["hizli"] == "celiski" for k in ilgili)
                 else "aday" if kaynakli else "cumle" if eklenen_var and kaynak_var else "yok")
        sonuc[o["id"]] = {"asama": asama, "guven": guven, "tur": o["tur"], "konum": o["konum"],
                          "yontem": o["yontem"],
                          "kaynakla_bulundu": any(eslesir(o, k["a"]["metin"], k["b"]["metin"]) for k in tespitler),
                          "benzerlik": max((k["benzerlik"] for k in kaynakli), default=None),
                          "oylar": [(k.get("hakem"), k.get("ikinci_gorus")) for k in tespitler]}
    fazladan = [k for k in kayit if k.get("guven") and not any(_iceriyor(o, k) for o in ogeler)]
    return {"maddeler": sonuc, "fazladan": fazladan}


def ozet(maddeler: dict, fazladan: int) -> dict:
    n = len(maddeler)
    # Bir aşamaya ulaşan = o aşamada ya da daha ilerisinde kalan ("yok" hiçbirine ulaşmadı)
    ulasan = {a: sum(1 for m in maddeler.values() if m["asama"] in ASAMALAR[i:]) for i, a in enumerate(ASAMALAR)}
    bulunan = ulasan["tespit"]
    return {"madde": n, "asamaya_ulasan": ulasan,
            "recall": round(bulunan / n, 3) if n else None,
            "recall_yuksek_guven": round(sum(m["guven"] == 1.0 for m in maddeler.values()) / n, 3) if n else None,
            "precision": round(bulunan / (bulunan + fazladan), 3) if bulunan + fazladan else None,
            "fazladan_tespit": fazladan}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Tutarlılık değerlendirmesi (K20)")
    ap.add_argument("--set", choices=("gelistirme", "test"), required=True)
    arg = ap.parse_args()

    ogeler = [o for o in set_yukle() if o["set"] == arg.set]
    rapor = {"set": arg.set, "kitaplar": {}}
    tum_maddeler, tum_fazladan = {}, []
    for kitap, yol in KITAPLAR.items():
        kitap_ogeleri = [o for o in ogeler if o["kitap"] == kitap]
        bloklar = celiskileri_uygula(bloklari_yukle(yol), kitap_ogeleri)
        onbellek_yolu = yol.with_name(f"{kitap}_tutarlilik_onbellek.json")
        onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
        kayit = []
        print(f"## {kitap}: {len(kitap_ogeleri)} madde eklendi", flush=True)
        haric = tutarlilik.alinti_haric(bloklar, yol.with_name(f"{kitap}.pdf"))  # alıntılar (K29)
        try:
            tutarlilik.analiz_et(bloklar, kayit=kayit, onbellek=onbellek, ilerleme=lambda m: print(" ", m, flush=True),
                                 haric=haric)
        finally:
            json_kaydet(onbellek, onbellek_yolu)
        # Tam kayıt: inceleyicinin test modu bunu gösterir (python -m derskitabi.inceleyici … --test-modu)
        json_kaydet(kayit, test_modu_kaydi_yolu(kitap, arg.set))
        kayit = [{**k, "a": {"metin": k["a"]["metin"], "sayfa_no": k["a"]["sayfa_no"]},
                  "b": {"metin": k["b"]["metin"], "sayfa_no": k["b"]["sayfa_no"]},
                  **{alan: k[alan]["karar"] for alan in ("hakem", "ikinci_gorus") if alan in k}} for k in kayit]
        cumleler = [c.metin for c in tutarlilik.bilgi_cumleleri(bloklar, haric)]
        p = puanla(kitap_ogeleri, cumleler, kayit)
        rapor["kitaplar"][kitap] = {"ozet": ozet(p["maddeler"], len(p["fazladan"])), **p}
        tum_maddeler.update(p["maddeler"])
        tum_fazladan += p["fazladan"]

    rapor["genel"] = ozet(tum_maddeler, len(tum_fazladan))
    for alan in ("tur", "konum", "yontem"):
        rapor[f"{alan}_gore"] = {d: ozet({k: m for k, m in tum_maddeler.items() if m[alan] == d}, 0)["recall"]
                                 for d in sorted({m[alan] for m in tum_maddeler.values()})}
    json_kaydet(rapor, PROJE / "veri" / f"degerlendirme_tutarlilik_{arg.set}.json")

    print(f"\n=== {arg.set}: {rapor['genel']['madde']} madde ===")
    print("Aşamaya ulaşan:", rapor["genel"]["asamaya_ulasan"])
    print(f"Recall {rapor['genel']['recall']} (yüksek güven {rapor['genel']['recall_yuksek_guven']}), "
          f"precision {rapor['genel']['precision']}, fazladan tespit {rapor['genel']['fazladan_tespit']}")
    for alan in ("tur", "konum", "yontem"):
        print(f"{alan}e göre recall:", rapor[f"{alan}_gore"])
    for k, m in sorted(tum_maddeler.items()):
        print(f"  {k}: {m['asama']:7} güven {m['guven']} kaynakla {m['kaynakla_bulundu']} benzerlik {m['benzerlik']} oylar {m['oylar']} ({m['tur']}, {m['konum']})")
    for k in tum_fazladan:
        print(f"  FAZLADAN [{k['guven']}] gemma4={k.get('hakem')} TG={k.get('ikinci_gorus')} s.{k['a']['sayfa_no']} \"{k['a']['metin'][:70]}\" / s.{k['b']['sayfa_no']} \"{k['b']['metin'][:70]}\"")


if __name__ == "__main__":
    main()
