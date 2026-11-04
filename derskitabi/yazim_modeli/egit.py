"""Yazım hata etiketleyicisinin eğitimi (K33): BERTurk + kelime başına sınıf.

Gece güvenliği:
  - KAYIT_DK dakikada bir kayıt noktası (model, iyileştirici, adım, rastgelelik); yeniden çalıştırılınca
    kaldığı adımdan devam eder. Kayıt önce geçici klasöre yazılır, sonra yer değiştirir (yarım kayıt kalmaz).
  - Bekçi her BEKCI_ADIM adımda bir: pilde, ekran kartı çok sıcak ya da RAM azsa bekletir.
  - Ekran kartı belleği yetmezse paket yarıya iner, gradyan biriktirme ikiye katlanır (etkin paket aynı kalır)
    ve son kayıttan devam edilir.
  - Geliştirme setinde her DEGERLENDIRME_ADIM adımda ölçülür; en iyi model (hata/doğru ikili F1) ayrıca
    saklanır; SABIR değerlendirme boyunca iyileşme yoksa erken durur.

Kullanım:
    python -m derskitabi.yazim_modeli.egit [--epok 3] [--saat 7]
"""

import torch  # noqa: I001 — Windows'ta pyarrow'dan önce yüklenmeli (DLL çakışması)

import argparse
import json
import math
import random
import shutil
import sys
import time
from pathlib import Path

from ..donanim import Bekci
from .etiketler import SINIFLAR

PROJE = Path(__file__).resolve().parents[2]
VERI = PROJE / "veri" / "yazim_modeli"
TABAN = PROJE / "modeller" / "dbmdz__bert-base-turkish-cased"
KLASOR = PROJE / "modeller" / "yazim_modeli"
EN_IYI = KLASOR / "en_iyi"
KAYIT = KLASOR / "kayit"
GUNLUK = VERI / "egitim.log"
EN_UZUN = 128  # alt kelime
KAYIT_DK = 20
BEKCI_ADIM = 25
DEGERLENDIRME_ADIM = 2000
SABIR = 4
GELISTIRME_EN_FAZLA = 6000
EN_AZ_BOS_GB = 4


def yaz(m: str) -> None:
    satir = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {m}"
    print(satir, flush=True)
    with open(GUNLUK, "a", encoding="utf-8") as g:
        g.write(satir + "\n")


def oku(ad: str, en_fazla: int | None = None) -> list[dict]:
    ornekler = [json.loads(s) for s in open(VERI / f"{ad}.jsonl", encoding="utf-8")]
    return ornekler[:en_fazla] if en_fazla else ornekler


def kodla(tokenizer, ornekler: list[dict]) -> list[dict]:
    """Kelime etiketi ilk alt kelimeye; diğer alt kelimeler ve özel imler -100 (kayba girmez)."""
    sonuc = []
    for i in range(0, len(ornekler), 2000):
        parca = ornekler[i:i + 2000]
        kod = tokenizer([o["kelimeler"] for o in parca], is_split_into_words=True, truncation=True,
                        max_length=EN_UZUN)
        for j, o in enumerate(parca):
            onceki, etiket = None, []
            for w in kod.word_ids(j):
                etiket.append(-100 if w is None or w == onceki else o["etiketler"][w])
                onceki = w
            sonuc.append({"input_ids": kod["input_ids"][j], "attention_mask": kod["attention_mask"][j],
                          "labels": etiket})
    return sonuc


def paketle(ornekler: list[dict], pad_id: int, aygit) -> dict:
    n = max(len(o["input_ids"]) for o in ornekler)
    def doldur(anahtar, deger):  # noqa: E306
        return torch.tensor([o[anahtar] + [deger] * (n - len(o[anahtar])) for o in ornekler], device=aygit)
    return {"input_ids": doldur("input_ids", pad_id), "attention_mask": doldur("attention_mask", 0),
            "labels": doldur("labels", -100)}


@torch.no_grad()
def degerlendir(model, veri: list[dict], pad_id: int, aygit, paket: int = 64) -> dict:
    """Kelime düzeyinde: ikili (hata / doğru) P, R, F1 ve sınıf başına F1."""
    model.eval()
    dp = yp = yn = 0
    sinif = {s: [0, 0, 0] for s in SINIFLAR[1:]}  # dp, yp, yn
    for i in range(0, len(veri), paket):
        b = paketle(veri[i:i + paket], pad_id, aygit)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            tahmin = model(input_ids=b["input_ids"], attention_mask=b["attention_mask"]).logits.argmax(-1)
        maske = b["labels"] != -100
        g, t = b["labels"][maske], tahmin[maske]
        dp += int(((g > 0) & (t > 0)).sum())
        yp += int(((g == 0) & (t > 0)).sum())
        yn += int(((g > 0) & (t == 0)).sum())
        for k, s in enumerate(SINIFLAR[1:], start=1):
            sinif[s][0] += int(((g == k) & (t == k)).sum())
            sinif[s][1] += int(((g != k) & (t == k)).sum())
            sinif[s][2] += int(((g == k) & (t != k)).sum())
    model.train()
    def f1(a, b_, c):  # noqa: E306
        p, r = a / max(1, a + b_), a / max(1, a + c)
        return round(p, 4), round(r, 4), round(2 * p * r / max(1e-9, p + r), 4)
    p, r, f = f1(dp, yp, yn)
    return {"P": p, "R": r, "F1": f, "sinif_F1": {s: f1(*v)[2] for s, v in sinif.items()}}


def _kaydet_atomik(hedef: Path, yaz_fn) -> None:
    bos = shutil.disk_usage(hedef.parent if hedef.parent.exists() else PROJE).free / 1024 ** 3
    if bos < EN_AZ_BOS_GB:  # disk dolarsa sistem de zarar görür: kayıt atlanır, eğitim sürer
        yaz(f"  ⚠ Diskte {bos:.1f} GB boş: kayıt atlandı ({hedef.name}).")
        return
    gecici = hedef.with_name(hedef.name + "_yaziliyor")
    if gecici.exists():
        shutil.rmtree(gecici)
    gecici.mkdir(parents=True)
    yaz_fn(gecici)
    if hedef.exists():
        shutil.rmtree(hedef)
    gecici.rename(hedef)


def egit(epok: int = 3, saat: float | None = None, paket: int = 32, ogrenme: float = 3e-5, tohum: int = 33) -> dict:
    from transformers import AutoModelForTokenClassification, AutoTokenizer, get_linear_schedule_with_warmup
    KLASOR.mkdir(parents=True, exist_ok=True)
    aygit = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    yaz(f"Aygıt: {aygit} {torch.cuda.get_device_name(0) if aygit.type == 'cuda' else ''}")
    tokenizer = AutoTokenizer.from_pretrained(TABAN)
    egitim = kodla(tokenizer, oku("egitim"))
    gelistirme = kodla(tokenizer, oku("gelistirme", GELISTIRME_EN_FAZLA))
    yaz(f"Veri: eğitim {len(egitim)}, geliştirme {len(gelistirme)} cümle")

    durum = {"adim": 0, "paket": paket, "biriktir": 1, "en_iyi_f1": -1.0, "sabir": 0, "gecmis": []}
    kaynak = TABAN
    if (KAYIT / "durum.json").exists():
        durum = json.loads((KAYIT / "durum.json").read_text(encoding="utf-8"))
        kaynak = KAYIT
        yaz(f"Kayıttan devam: adım {durum['adim']}, paket {durum['paket']}×{durum['biriktir']}")
    model = AutoModelForTokenClassification.from_pretrained(
        kaynak, num_labels=len(SINIFLAR), id2label=dict(enumerate(SINIFLAR)),
        label2id={s: i for i, s in enumerate(SINIFLAR)}).to(aygit)
    etkin = durum["paket"] * durum["biriktir"]
    adim_epok = math.ceil(len(egitim) / etkin)
    toplam = adim_epok * epok
    opt = torch.optim.AdamW(model.parameters(), lr=ogrenme, weight_decay=0.01)
    plan = get_linear_schedule_with_warmup(opt, int(0.06 * toplam), toplam)
    if kaynak == KAYIT and (KAYIT / "iyilestirici.pt").exists():
        d = torch.load(KAYIT / "iyilestirici.pt", map_location=aygit, weights_only=False)
        opt.load_state_dict(d["opt"])
        plan.load_state_dict(d["plan"])
    bekci = Bekci(yaz)
    bitis = time.time() + saat * 3600 if saat else None
    son_kayit = time.time()
    pad = tokenizer.pad_token_id
    model.train()

    def kayit_al():
        def yaz_fn(k):
            model.save_pretrained(k)
            torch.save({"opt": opt.state_dict(), "plan": plan.state_dict()}, k / "iyilestirici.pt")
            (k / "durum.json").write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
        _kaydet_atomik(KAYIT, yaz_fn)

    baslangic, bas_adim = time.time(), durum["adim"]
    while durum["adim"] < toplam:
        e = durum["adim"] // adim_epok
        sira = list(range(len(egitim)))
        random.Random(tohum + e).shuffle(sira)
        for a in range(durum["adim"] % adim_epok, adim_epok):
            secim = sira[a * etkin:(a + 1) * etkin]
            if not secim:
                break
            kayip_toplam = 0.0
            for k in range(durum["biriktir"]):
                parca = [egitim[i] for i in secim[k * durum["paket"]:(k + 1) * durum["paket"]]]
                if not parca:
                    continue
                b = paketle(parca, pad, aygit)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    kayip = model(**b).loss / durum["biriktir"]
                kayip.backward()
                kayip_toplam += float(kayip)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            plan.step()
            opt.zero_grad(set_to_none=True)
            durum["adim"] += 1
            n = durum["adim"]
            if n % BEKCI_ADIM == 0:
                bekci.adim()
            if n % 200 == 0:
                hiz = (time.time() - baslangic) / max(1, n - bas_adim)
                kalan = (toplam - n) * hiz / 3600
                yaz(f"adım {n}/{toplam} (epok {e + 1}) kayıp {kayip_toplam:.4f} · kalan ~{kalan:.1f} sa")
            if n % DEGERLENDIRME_ADIM == 0 or n == toplam:
                sonuc = degerlendir(model, gelistirme, pad, aygit)
                durum["gecmis"].append({"adim": n, **sonuc})
                yaz(f"geliştirme: {sonuc}")
                if sonuc["F1"] > durum["en_iyi_f1"]:
                    durum["en_iyi_f1"], durum["sabir"] = sonuc["F1"], 0
                    _kaydet_atomik(EN_IYI, lambda k: (model.save_pretrained(k), tokenizer.save_pretrained(k)))
                    yaz(f"  en iyi model kaydedildi (F1 {sonuc['F1']})")
                else:
                    durum["sabir"] += 1
                    if durum["sabir"] >= SABIR:
                        yaz("Erken durdurma: geliştirme F1 iyileşmiyor.")
                        kayit_al()
                        return durum
            if time.time() - son_kayit > KAYIT_DK * 60:
                kayit_al()
                son_kayit = time.time()
            if bitis and time.time() > bitis:
                yaz("Süre sınırı: kayıt alınıp duruluyor.")
                kayit_al()
                return durum
    kayit_al()
    yaz(f"Eğitim bitti. En iyi geliştirme F1: {durum['en_iyi_f1']}")
    return durum


def calistir(epok: int, saat: float | None) -> dict:
    """Bellek yetmezse paketi küçültüp kayıttan devam eder."""
    paket = 32
    while True:
        try:
            return egit(epok, saat, paket)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if not (KAYIT / "durum.json").exists():
                paket //= 2
                if paket < 4:
                    raise
                yaz(f"Ekran kartı belleği yetmedi: paket {paket} ile baştan.")
                continue
            d = json.loads((KAYIT / "durum.json").read_text(encoding="utf-8"))
            if d["paket"] <= 4:
                raise
            d["paket"] //= 2
            d["biriktir"] *= 2
            (KAYIT / "durum.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            yaz(f"Ekran kartı belleği yetmedi: paket {d['paket']}×{d['biriktir']} ile kayıttan devam.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Yazım hata etiketleyicisi eğitimi (K33)")
    ap.add_argument("--epok", type=int, default=3)
    ap.add_argument("--saat", type=float, help="Süre sınırı (saat); dolunca kayıt alıp durur")
    arg = ap.parse_args()
    VERI.mkdir(parents=True, exist_ok=True)
    calistir(arg.epok, arg.saat)
