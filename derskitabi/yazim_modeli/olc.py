"""K33 ölçümleri (ölçüt ve karar kuralı eğitimden önce KARARLAR.md K33'te yazıldı).

  E1 TDE 10 yapay hatalar (görülmemiş kitap)        E2 GECTurk test + film yorumları
  E3 Vikipedi gerçek hatalar (görülmemiş sayfalar)   E4 kilitli yazım test seti (eklenmiş 56 hata)
  E5 etiketli 37 gerçek kitap hatası                 E6 sistemin etiketli 331 yanlış alarmı
  E7 modelin sistemden bağımsız yeni tespitleri (görülmemiş sayfalarda; 60'ı körlemesine etiketlenecek)
Karşılaştırma: GECTurk'ün hazır modeli (GGLab/gec-tr-seq-tagger), E1–E6'da.

Kullanım:
    python -m derskitabi.yazim_modeli.olc [--model modeller/yazim_modeli/en_iyi]
"""

import torch  # noqa: I001 — pyarrow'dan önce

import argparse
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

from ..degerlendirme import celiskileri_uygula
from ..kayit import bloklari_yukle, tespitleri_yukle
from ..kriterler.okunabilirlik import cumlelere_bol
from .egit import EN_IYI, VERI
from .etiketler import SINIFLAR, gecturk_sinifi

PROJE = Path(__file__).resolve().parents[2]
TESTSETI = PROJE / "testseti"
GECTURK_MODELI = PROJE / "modeller" / "GGLab__gec-tr-seq-tagger"
ESIK = 0.5
AYGIT = "cuda" if torch.cuda.is_available() and not os.environ.get("YAZIM_MODELI_CPU") else "cpu"


class Etiketleyici:
    """Kelime listelerine hata olasılığı ve sınıf verir. gecturk=True: GGLab modeli (etiketler rule_k)."""

    def __init__(self, yol: Path, gecturk: bool = False):
        from transformers import AutoModelForTokenClassification, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(yol)
        self.model = AutoModelForTokenClassification.from_pretrained(yol).to(AYGIT).eval()
        self.gecturk = gecturk
        etiketler = self.model.config.id2label
        self.sinif = [gecturk_sinifi(int(etiketler[i].split("_")[-1])) if gecturk and etiketler[i] != "O"
                      else (0 if gecturk else i) for i in range(len(etiketler))]

    @torch.no_grad()
    def __call__(self, cumleler: list[list[str]], paket: int = 64) -> list[list[tuple[float, int]]]:
        """Her kelime için (hata olasılığı, sınıf)."""
        sonuc = []
        for i in range(0, len(cumleler), paket):
            parca = [c[:100] for c in cumleler[i:i + paket]]
            kod = self.tok(parca, is_split_into_words=True, truncation=True, max_length=192, padding=True,
                           return_tensors="pt").to(AYGIT)
            with torch.autocast(AYGIT, dtype=torch.bfloat16, enabled=AYGIT == "cuda"):
                olas = self.model(**kod).logits.float().softmax(-1)
            for j, c in enumerate(cumleler[i:i + paket]):
                kelime = [(0.0, 0)] * len(c)
                onceki = None
                for t, w in enumerate(kod.word_ids(j)):
                    if w is None or w == onceki:
                        continue
                    onceki = w
                    p = olas[j, t]
                    hata = float(1 - p[0])  # 0 = DOGRU (GECTurk modelinde "O")
                    k = int(p[1:].argmax()) + 1
                    kelime[w] = (hata, self.sinif[k])
                sonuc.append(kelime)
        return sonuc


def metni_etiketle(et: Etiketleyici, metinler: list[str]) -> list[list[tuple[int, int, str, float, int]]]:
    """Her metin için [(başlangıç, bitiş, kelime, hata olasılığı, sınıf)]; metin cümlelere bölünür."""
    parcalar, nereye = [], []
    for mi, metin in enumerate(metinler):
        imlec = 0
        for c in cumlelere_bol(metin) or [metin]:
            bas = metin.find(c, imlec)
            if bas < 0:
                bas = imlec
            imlec = bas + len(c)
            kelimeler = [(bas + m.start(), bas + m.end(), m.group()) for m in re.finditer(r"\S+", c)]
            for k in range(0, len(kelimeler), 80):
                parcalar.append(kelimeler[k:k + 80])
                nereye.append(mi)
    tahmin = et([[w for _, _, w in p] for p in parcalar])
    sonuc = [[] for _ in metinler]
    for mi, p, t in zip(nereye, parcalar, tahmin):
        sonuc[mi].extend((a, b, w, h, s) for (a, b, w), (h, s) in zip(p, t))
    return sonuc


def jsonl(ad: str) -> list[dict]:
    yol = VERI / f"{ad}.jsonl"
    return [json.loads(s) for s in open(yol, encoding="utf-8")] if yol.exists() else []


def kelime_olcumu(et: Etiketleyici, ornekler: list[dict], esik: float = ESIK) -> dict:
    """Kelime düzeyinde ikili hata P/R/F1 ve (bizim modelde) sınıf başına recall."""
    if not ornekler:
        return {}
    tahmin = et([o["kelimeler"] for o in ornekler])
    dp = yp = yn = 0
    sinif = Counter()
    sinif_bulunan = Counter()
    for o, t in zip(ornekler, tahmin):
        for g, (h, s) in zip(o["etiketler"], t):
            bul = h >= esik
            dp += g > 0 and bul
            yp += g == 0 and bul
            yn += g > 0 and not bul
            if g > 0:
                sinif[SINIFLAR[g]] += 1
                sinif_bulunan[SINIFLAR[g]] += bul
    p, r = dp / max(1, dp + yp), dp / max(1, dp + yn)
    return {"P": round(p, 3), "R": round(r, 3), "F1": round(2 * p * r / max(1e-9, p + r), 3), "hata": dp + yn,
            "sinif_recall": {s: f"{sinif_bulunan[s]}/{n}" for s, n in sinif.items()}}


def _degisen_aralik(oge: dict, metin: str) -> tuple[int, int]:
    """Eklenen hatanın metindeki karakter aralığı (eski ile yeni ifadenin farklı kısmı)."""
    eski, yeni = oge["hedef"]["eski"], oge["hedef"]["yeni"]
    bas = metin.find(yeni)
    o = 0
    while o < min(len(eski), len(yeni)) and eski[o] == yeni[o]:
        o += 1
    s = 0
    while s < min(len(eski), len(yeni)) - o and eski[-1 - s] == yeni[-1 - s]:
        s += 1
    return bas + o, bas + max(o + 1, len(yeni) - s)


def e4_kilitli(et: Etiketleyici) -> dict:
    ogeler = [o for o in json.loads((TESTSETI / "yazim_hatalari.json").read_text(encoding="utf-8"))]
    sonuc = {}
    for kitap in sorted({o["kitap"] for o in ogeler}):
        oo = [o for o in ogeler if o["kitap"] == kitap]
        degismis = {(b.sayfa_no, b.blok_no): b for b in celiskileri_uygula(
            bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json"), oo)}
        metinler = [degismis[(o["sayfa_no"], o["blok_no"])].metin for o in oo]
        for o, metin, kel in zip(oo, metinler, metni_etiketle(et, metinler)):
            a, b = _degisen_aralik(o, metin)
            en = max((h for s, e, _, h, _ in kel if s < b and e > a), default=0.0)
            sonuc[o["id"]] = {"set": o["set"], "tur": o["tur"], "alt_tur": o["alt_tur"], "olasilik": round(en, 3)}
    ozet = {}
    for st in ("test", "gelistirme"):
        m = [v for v in sonuc.values() if v["set"] == st]
        ozet[st] = {"bulunan": sum(v["olasilik"] >= ESIK for v in m), "toplam": len(m),
                    "tur": {t: f"{sum(v['olasilik'] >= ESIK for v in m if v['alt_tur'] == t)}/"
                               f"{sum(v['alt_tur'] == t for v in m)}" for t in sorted({v['alt_tur'] for v in m})}}
    return {"ozet": ozet, "maddeler": sonuc}


def etiketli_tespitler(et: Etiketleyici) -> list[dict]:
    """Etiketli sistem tespitleri (gerçek / sahte) ve modelin o kelimeye verdiği en yüksek hata olasılığı."""
    sonuc = []
    for ad in ("yazim_etiketler", "yazim_etiketler_test", "yazim_etiketler_k29"):
        ogeler = json.loads((TESTSETI / f"{ad}.json").read_text(encoding="utf-8"))
        ogeler = ogeler if isinstance(ogeler, list) else next(v for v in ogeler.values() if isinstance(v, list))
        ogeler = [o for o in ogeler if o.get("etiket") in ("gercek", "sahte")]
        bloklar = {}
        for kitap in {o["kitap"] for o in ogeler}:
            bloklar[kitap] = {(b.sayfa_no, b.blok_no): b for b in bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")}
        metinler = [bloklar[o["kitap"]][(o["sayfa_no"], o["blok_no"])].metin for o in ogeler]
        for o, metin, kel in zip(ogeler, metinler, metni_etiketle(et, metinler)):
            parca = (o.get("parca") or "").strip()
            a = metin.find(parca) if parca else -1
            if a < 0:
                en = None
            else:
                b = a + len(parca)
                en = max((h for s, e, _, h, _ in kel if s < b and e > a), default=0.0)
            sonuc.append({"set": ad, "id": o["id"], "etiket": o["etiket"], "sebep": o.get("sebep"),
                          "parca": parca, "olasilik": None if en is None else round(en, 3)})
    return sonuc


def suzgec(etiketli: list[dict]) -> dict:
    """K33 B: τ geliştirme etiketlerinde seçilir (gerçek kaybı ≤ 1, en çok sahte düşer), K29'da sınanır.
    Model "doğru" der: hata olasılığı < τ."""
    gel = [o for o in etiketli if o["set"] != "yazim_etiketler_k29" and o["olasilik"] is not None]
    test = [o for o in etiketli if o["set"] == "yazim_etiketler_k29" and o["olasilik"] is not None]
    en_iyi = None
    for tau in [x / 100 for x in range(1, 100)]:
        kayip = sum(o["etiket"] == "gercek" and o["olasilik"] < tau for o in gel)
        dusen = sum(o["etiket"] == "sahte" and o["olasilik"] < tau for o in gel)
        if kayip <= 1 and (en_iyi is None or dusen > en_iyi[1]):
            en_iyi = (tau, dusen, kayip)
    tau = en_iyi[0] if en_iyi else 0.0
    t_kayip = sum(o["etiket"] == "gercek" and o["olasilik"] < tau for o in test)
    t_sahte = sum(o["etiket"] == "sahte" for o in test)
    t_dusen = sum(o["etiket"] == "sahte" and o["olasilik"] < tau for o in test)
    return {"tau": tau, "gelistirme": {"sahte_dusen": en_iyi[1] if en_iyi else 0,
                                        "sahte": sum(o["etiket"] == "sahte" for o in gel),
                                        "gercek_kayip": en_iyi[2] if en_iyi else 0,
                                        "gercek": sum(o["etiket"] == "gercek" for o in gel)},
            "k29": {"sahte_dusen": t_dusen, "sahte": t_sahte, "gercek_kayip": t_kayip,
                    "gercek": sum(o["etiket"] == "gercek" for o in test)},
            "gecti": t_kayip == 0 and t_sahte > 0 and t_dusen / t_sahte >= 0.40}


def e7_yeni_tespitler(et: Etiketleyici, ornek: int = 60, tohum: int = 7) -> dict:
    """Görülmemiş sayfalar (TDE 10 tamamı + test sayfaları): modelin, sistemin tespit etmediği kelimelerde
    verdiği tespitler. 60'ı rastgele seçilip olasılıksız olarak etiketleme dosyasına yazılır."""
    from .veri import DENEME_KITABI, EGITIM_KITAPLARI, test_sayfalari
    haric = test_sayfalari()
    adaylar, sayfa_say = [], 0
    for kitap in [DENEME_KITABI] + EGITIM_KITAPLARI:
        bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        sayfalar = None if kitap == DENEME_KITABI else haric.get(kitap, set())
        bloklar = [b for b in bloklar if b.tur in ("paragraf", "kisa") and (sayfalar is None or b.sayfa_no in sayfalar)]
        sayfa_say += len({b.sayfa_no for b in bloklar})
        sistem = set()
        yol = PROJE / "veri" / f"{kitap}_yazim_tespitler.json"
        if yol.exists():
            for t in tespitleri_yukle(yol):
                for w in (t.metin_parcasi or "").split():
                    sistem.add((t.sayfa_no, t.blok_no, w.strip(".,;:!?\"'()")))
        for b, kel in zip(bloklar, metni_etiketle(et, [b.metin for b in bloklar])):
            for s, e, w, h, k in kel:
                if h >= ESIK and (b.sayfa_no, b.blok_no, w.strip(".,;:!?\"'()")) not in sistem:
                    adaylar.append({"kitap": kitap, "sayfa_no": b.sayfa_no, "blok_no": b.blok_no, "kelime": w,
                                    "sinif": SINIFLAR[k], "baglam": b.metin[max(0, s - 80):e + 80],
                                    "olasilik": round(h, 3)})
    r = random.Random(tohum)
    secilen = r.sample(adaylar, min(ornek, len(adaylar)))
    etiketlenecek = [{"id": f"E7-{i + 1:02d}", **{k: v for k, v in o.items() if k != "olasilik"},
                      "etiket": None, "not": ""} for i, o in enumerate(secilen)]
    (VERI / "e7_etiketlenecek.json").write_text(json.dumps(etiketlenecek, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    (VERI / "e7_olasiliklar.json").write_text(json.dumps({f"E7-{i + 1:02d}": o["olasilik"] for i, o in
                                                          enumerate(secilen)}), encoding="utf-8")
    return {"yeni_tespit": len(adaylar), "sayfa": sayfa_say,
            "10_sayfada": round(10 * len(adaylar) / max(1, sayfa_say), 1),
            "sinif": dict(Counter(o["sinif"] for o in adaylar)), "etiketlenecek": len(etiketlenecek)}


def olc(model_yolu: Path = EN_IYI, ilerleme=print) -> dict:
    rapor = {}
    for ad, yol, gt in (("bizim", model_yolu, False), ("gecturk_hazir", GECTURK_MODELI, True)):
        if not Path(yol).exists():
            continue
        ilerleme(f"## {ad}: {yol}")
        et = Etiketleyici(Path(yol), gecturk=gt)
        r = {}
        for e, dosya in (("E1_tde10", "e1_tde10"), ("E2_gecturk_test", "e2_gecturk_test"), ("E2_film", "e2_film"),
                         ("E3_vikipedi", "e3_vikipedi")):
            r[e] = kelime_olcumu(et, jsonl(dosya))
            ilerleme(f"  {e}: {r[e]}")
        e4 = e4_kilitli(et)
        r["E4_kilitli"] = e4["ozet"]
        ilerleme(f"  E4: {e4['ozet']}")
        etiketli = etiketli_tespitler(et)
        gercek = [o for o in etiketli if o["etiket"] == "gercek" and o["olasilik"] is not None]
        sahte = [o for o in etiketli if o["etiket"] == "sahte" and o["olasilik"] is not None]
        r["E5_gercek_hatalar"] = f"{sum(o['olasilik'] >= ESIK for o in gercek)}/{len(gercek)}"
        r["E6_sahte_dogru_dedi"] = f"{sum(o['olasilik'] < ESIK for o in sahte)}/{len(sahte)}"
        r["E6_sebebe_gore"] = {s: f"{sum(o['olasilik'] < ESIK for o in sahte if o['sebep'] == s)}/"
                                  f"{sum(o['sebep'] == s for o in sahte)}" for s in sorted({str(o['sebep']) for o in sahte})}
        r["B_suzgec"] = suzgec(etiketli)
        ilerleme(f"  E5: {r['E5_gercek_hatalar']} · E6: {r['E6_sahte_dogru_dedi']} · süzgeç: {r['B_suzgec']}")
        if ad == "bizim":
            r["E7"] = e7_yeni_tespitler(et)
            ilerleme(f"  E7: {r['E7']}")
            (VERI / "olcum_maddeler.json").write_text(json.dumps({"E4": e4["maddeler"], "etiketli": etiketli},
                                                                 ensure_ascii=False, indent=1), encoding="utf-8")
        rapor[ad] = r
        del et
        torch.cuda.empty_cache()
    (VERI / "olcum.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    ilerleme("Ölçüm bitti: veri/yazim_modeli/olcum.json")
    return rapor


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="K33 ölçümleri")
    ap.add_argument("--model", type=Path, default=EN_IYI)
    olc(ap.parse_args().model, ilerleme=lambda m: print(m, flush=True))
