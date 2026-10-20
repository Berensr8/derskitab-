"""Değerlendirme: yazım kriterini bilerek eklenmiş hatalarla (recall) ve etiketlenmiş gerçek
tespitlerle (precision) ölçer (K23).

Recall  : testseti/yazim_hatalari.json'daki hatalar blok dosyasının kopyasına uygulanır, yazım
          kriteri tüm kitapta çalıştırılır; hata, aynı blokta beklenen türde ve aranan ifadeyi
          içeren bir tespit varsa bulunmuş sayılır. Eklenen hataların yeni sahte tespite yol açıp
          açmadığı da raporlanır.
Precision: testseti/yazim_etiketler.json — sistemin değiştirilmemiş kitaplardaki tespitleri
          (Sosyal Bilgiler 6'nın hepsi, Biyoloji 10'dan rastgele örneklem) tek tek "gercek" /
          "sahte" diye etiketlendi.

Kural (K20/K23): ayar yaparken yalnız geliştirme maddeleri; test maddeleri en sonda bir kez.

Kullanım:
    python -m derskitabi.degerlendirme_yazim --set gelistirme
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .degerlendirme import PROJE, celiskileri_uygula, set_yukle
from .kayit import bloklari_yukle, json_kaydet
from .kriterler import yazim
from .model import Tespit

SET_YOLU = PROJE / "testseti" / "yazim_hatalari.json"
KILIT_SHA256 = "097538e7e972d9f9ecab5efff2dc9f7beb68415451a924684cb2f4c34444ee71"  # K23
ETIKET_YOLU = PROJE / "testseti" / "yazim_etiketler.json"
KITAPLAR = ("kitap", "biyoloji10")


def _cekirdek(oge: dict) -> str:
    """Tespit parçasında aranacak ifade. Noktalama kuralı parçayı işaretin ±12 karakteri olarak
    kaydeder ("sakkaritlere,yağlar glise"); bu yüzden orada işaretin çevresine bakılır."""
    if oge["alt_tur"] == "noktalama_bosluk":
        once, sonra = oge["aranan"].split(",", 1)
        return f"{once[-5:]},{sonra[:5]}"
    return oge["aranan"]


def bulundu_mu(oge: dict, tespitler: list[Tespit]) -> float:
    """Bulunduysa en yüksek güven, bulunmadıysa 0."""
    return max((t.guven_skoru for t in tespitler
                if (t.sayfa_no, t.blok_no) == (oge["sayfa_no"], oge["blok_no"])
                and t.alt_tur == oge["beklenen_alt_tur"] and _cekirdek(oge) in (t.metin_parcasi or "")),
               default=0.0)


def _anahtar(t: Tespit) -> tuple:
    return t.sayfa_no, t.blok_no, t.alt_tur, t.metin_parcasi


def recall_olc(ogeler: list[dict], bloklar, taban: list[Tespit], denetciler=None) -> dict:
    degismis = celiskileri_uygula(bloklar, ogeler)
    tespitler = yazim.analiz_et(degismis, denetciler, kitap_bloklari=degismis)
    sonuc = {o["id"]: {"guven": bulundu_mu(o, tespitler), "tur": o["tur"], "alt_tur": o["alt_tur"]}
             for o in ogeler}
    eklenen_bloklar = {(o["sayfa_no"], o["blok_no"]) for o in ogeler}
    taban_anahtar = {_anahtar(t) for t in taban}
    # Eklenen hatanın kendisi dışında yeni ortaya çıkan tespitler (ör. hata komşu kelimeyi de etkiledi)
    yeni = [t for t in tespitler if _anahtar(t) not in taban_anahtar
            and not any(bulundu_mu(o, [t]) for o in ogeler)]
    return {"maddeler": sonuc, "yeni_sahte": [{"sayfa_no": t.sayfa_no, "blok_no": t.blok_no,
                                                "alt_tur": t.alt_tur, "parca": t.metin_parcasi,
                                                "eklenen_blokta": (t.sayfa_no, t.blok_no) in eklenen_bloklar}
                                               for t in yeni]}


def precision_olc() -> dict | None:
    if not ETIKET_YOLU.exists():
        return None
    etiketler = json.loads(ETIKET_YOLU.read_text(encoding="utf-8"))
    sonuc = {}
    for kitap in KITAPLAR:
        tum = [x for x in etiketler if x["kitap"] == kitap]
        e = [x for x in tum if x["etiket"] != "belirsiz"]  # belirsizler paydaya katılmaz, ayrıca sayılır
        if not e:
            continue
        gercek = sum(x["etiket"] == "gercek" for x in e)
        yuksek = [x for x in e if x["guven"] >= 1.0]
        sonuc[kitap] = {"etiketlenen": len(tum), "belirsiz": len(tum) - len(e), "gercek": gercek,
                        "precision": round(gercek / len(e), 3),
                        "precision_yuksek_guven": round(sum(x["etiket"] == "gercek" for x in yuksek) / len(yuksek), 3)
                        if yuksek else None,
                        "sahte_sebepleri": Counter(x.get("sebep", "?") for x in e if x["etiket"] == "sahte").most_common()}
    return sonuc


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Yazım değerlendirmesi (K23)")
    ap.add_argument("--set", choices=("gelistirme", "test"), required=True)
    arg = ap.parse_args()

    ogeler = [o for o in set_yukle(SET_YOLU, KILIT_SHA256) if o["set"] == arg.set]
    maddeler, yeni_sahte = {}, []
    for kitap in KITAPLAR:
        bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        taban = [Tespit.sozlukten(t) for t in
                 json.loads((PROJE / "veri" / f"{kitap}_yazim_tespitler.json").read_text(encoding="utf-8"))]
        r = recall_olc([o for o in ogeler if o["kitap"] == kitap], bloklar, taban)
        maddeler.update(r["maddeler"])
        yeni_sahte += r["yeni_sahte"]

    n = len(maddeler)
    bulunan = sum(1 for m in maddeler.values() if m["guven"])
    rapor = {"set": arg.set, "madde": n, "recall": round(bulunan / n, 3),
             "recall_yuksek_guven": round(sum(m["guven"] >= 1.0 for m in maddeler.values()) / n, 3),
             "ture_gore": {t: round(sum(1 for m in maddeler.values() if m["alt_tur"] == t and m["guven"]) /
                                    sum(1 for m in maddeler.values() if m["alt_tur"] == t), 3)
                           for t in sorted({m["alt_tur"] for m in maddeler.values()})},
             "yeni_sahte_tespit": yeni_sahte, "precision": precision_olc(), "maddeler": maddeler}
    json_kaydet(rapor, PROJE / "veri" / f"degerlendirme_yazim_{arg.set}.json")

    print(f"=== yazım {arg.set}: {n} madde ===")
    print(f"Recall {rapor['recall']} ({bulunan}/{n}), yüksek güven {rapor['recall_yuksek_guven']}")
    print("Türe göre:", rapor["ture_gore"])
    print(f"Eklenen hataların yol açtığı yeni sahte tespit: {len(yeni_sahte)}", yeni_sahte[:5])
    for k, m in sorted(maddeler.items()):
        if not m["guven"]:
            o = next(x for x in ogeler if x["id"] == k)
            print(f"  KAÇAN {k} ({m['alt_tur']}): {o['hedef']['yeni']}")
    print("Precision (etiketlerden):", json.dumps(rapor["precision"], ensure_ascii=False))


if __name__ == "__main__":
    main()
