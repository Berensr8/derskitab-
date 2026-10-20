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

--hakem (K25): tespitler yazım hakemine (dil modeli) danışılır; bulunmuş/doğru sayılan tespitler
güveni 0,5 ve üstü olanlardır (hakemin "muhtemelen doğru" dediği tespitler 0,25'e iner). Precision
geliştirmede yazim_etiketler.json (Sosyal 6, Biyoloji 10), testte yazim_etiketler_test.json
(Matematik 11, TDE 9 — hakem çalıştırılmadan önce etiketlendi) ile ölçülür.

Kullanım:
    python -m derskitabi.degerlendirme_yazim --set gelistirme [--hakem]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .degerlendirme import PROJE, celiskileri_uygula, set_yukle
from .kayit import bloklari_yukle, json_kaydet
from .kriterler import yazim, yazim_hakem
from .model import Tespit

SET_YOLU = PROJE / "testseti" / "yazim_hatalari.json"
KILIT_SHA256 = "097538e7e972d9f9ecab5efff2dc9f7beb68415451a924684cb2f4c34444ee71"  # K23
ETIKET_YOLLARI = {"gelistirme": PROJE / "testseti" / "yazim_etiketler.json",
                  "test": PROJE / "testseti" / "yazim_etiketler_test.json"}
TEST_ETIKET_SHA256 = "7e5215710ca5325744209764da33bdb82fb03a3647e41b054ce23969fe1de438"  # K25, hakemden önce
HAKEM_ONBELLEK = PROJE / "veri" / "yazim_hakem_onbellek.json"
ESIK = 0.5  # hakemli değerlendirmede "gösterilen" tespit
KITAPLAR = ("kitap", "biyoloji10")


def _onbellek_yukle() -> dict:
    return json.loads(HAKEM_ONBELLEK.read_text(encoding="utf-8")) if HAKEM_ONBELLEK.exists() else {}


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


def recall_olc(ogeler: list[dict], bloklar, taban: list[Tespit], denetciler=None,
               hakem_onbellegi: dict | None = None) -> dict:
    degismis = celiskileri_uygula(bloklar, ogeler)
    tespitler = yazim.analiz_et(degismis, denetciler, kitap_bloklari=degismis)
    if hakem_onbellegi is not None:
        tespitler = yazim_hakem.hakemle(tespitler, degismis, onbellek=hakem_onbellegi, ilerleme=print)
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


def precision_olc(set_adi: str = "gelistirme", hakem_onbellegi: dict | None = None) -> dict | None:
    yol = ETIKET_YOLLARI[set_adi]
    if not yol.exists():
        return None
    etiketler = (set_yukle(yol, TEST_ETIKET_SHA256) if set_adi == "test"
                 else json.loads(yol.read_text(encoding="utf-8")))
    if hakem_onbellegi is not None:  # etiketli tespitleri hakeme danış, güvenlerini güncelle
        for kitap in sorted({x["kitap"] for x in etiketler}):
            e = [x for x in etiketler if x["kitap"] == kitap]
            tespitler = [Tespit(x["sayfa_no"], x["blok_no"], (0, 0, 1, 1), "yazim", "", x["guven"],
                                alt_tur=x["alt_tur"], metin_parcasi=x["parca"]) for x in e]
            yeni = yazim_hakem.hakemle(tespitler, bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json"),
                                       onbellek=hakem_onbellegi, ilerleme=print)
            for x, t in zip(e, yeni):
                x["guven_once"], x["guven"] = x["guven"], t.guven_skoru
                x["gosterilir"] = t.guven_skoru >= ESIK
    sonuc = {}
    for kitap in sorted({x["kitap"] for x in etiketler}):
        tum = [x for x in etiketler if x["kitap"] == kitap]
        if hakem_onbellegi is not None:
            kaybolan = [x["parca"] for x in tum if x["etiket"] == "gercek" and not x["gosterilir"]]
            tum = [x for x in tum if x["gosterilir"]]
        else:
            kaybolan = None
        e = [x for x in tum if x["etiket"] != "belirsiz"]  # belirsizler paydaya katılmaz, ayrıca sayılır
        if not e:
            continue
        gercek = sum(x["etiket"] == "gercek" for x in e)
        yuksek = [x for x in e if x["guven"] >= 1.0]
        sonuc[kitap] = {"etiketlenen": len(tum), "belirsiz": len(tum) - len(e), "gercek": gercek,
                        "precision": round(gercek / len(e), 3),
                        "precision_yuksek_guven": round(sum(x["etiket"] == "gercek" for x in yuksek) / len(yuksek), 3)
                        if yuksek else None,
                        "sahte_sebepleri": Counter(x.get("sebep", "?") for x in e if x["etiket"] == "sahte").most_common(),
                        "gosterilen": len(tum), "dusuk_oncelige_inen_gercek_hata": kaybolan}
    return sonuc


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Yazım değerlendirmesi (K23)")
    ap.add_argument("--set", choices=("gelistirme", "test"), required=True)
    ap.add_argument("--hakem", action="store_true", help="Yazım hakemiyle (dil modeli, K25)")
    arg = ap.parse_args()
    onbellek = _onbellek_yukle() if arg.hakem else None

    ogeler = [o for o in set_yukle(SET_YOLU, KILIT_SHA256) if o["set"] == arg.set]
    maddeler, yeni_sahte = {}, []
    for kitap in KITAPLAR:
        bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        taban = [Tespit.sozlukten(t) for t in
                 json.loads((PROJE / "veri" / f"{kitap}_yazim_tespitler.json").read_text(encoding="utf-8"))]
        try:
            r = recall_olc([o for o in ogeler if o["kitap"] == kitap], bloklar, taban, hakem_onbellegi=onbellek)
        finally:
            if onbellek is not None:
                json_kaydet(onbellek, HAKEM_ONBELLEK)
        maddeler.update(r["maddeler"])
        yeni_sahte += r["yeni_sahte"]

    n = len(maddeler)
    esik = ESIK if arg.hakem else 1e-9
    for m in maddeler.values():  # hakemli: düşük önceliğe inen (0,25) bulunmamış sayılır
        m["bulundu"] = m["guven"] >= esik
    bulunan = sum(m["bulundu"] for m in maddeler.values())
    rapor = {"set": arg.set, "madde": n, "recall": round(bulunan / n, 3),
             "recall_yuksek_guven": round(sum(m["guven"] >= 1.0 for m in maddeler.values()) / n, 3),
             "ture_gore": {t: round(sum(1 for m in maddeler.values() if m["alt_tur"] == t and m["bulundu"]) /
                                    sum(1 for m in maddeler.values() if m["alt_tur"] == t), 3)
                           for t in sorted({m["alt_tur"] for m in maddeler.values()})},
             "yeni_sahte_tespit": yeni_sahte, "maddeler": maddeler}
    try:
        rapor["precision"] = precision_olc(arg.set, onbellek)
    finally:
        if onbellek is not None:
            json_kaydet(onbellek, HAKEM_ONBELLEK)
    json_kaydet(rapor, PROJE / "veri" / f"degerlendirme_yazim_{arg.set}{'_hakem' if arg.hakem else ''}.json")

    print(f"=== yazım {arg.set}: {n} madde ===")
    print(f"Recall {rapor['recall']} ({bulunan}/{n}), yüksek güven {rapor['recall_yuksek_guven']}")
    print("Türe göre:", rapor["ture_gore"])
    print(f"Eklenen hataların yol açtığı yeni sahte tespit: {len(yeni_sahte)}", yeni_sahte[:5])
    for k, m in sorted(maddeler.items()):
        if not m["bulundu"]:
            o = next(x for x in ogeler if x["id"] == k)
            print(f"  KAÇAN {k} ({m['alt_tur']}): {o['hedef']['yeni']}")
    print("Precision (etiketlerden):")
    for kitap, v in (rapor["precision"] or {}).items():
        print(f"  {kitap}: {json.dumps(v, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
