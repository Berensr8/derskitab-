"""K34 kesme işareti denetimi ölçümü (ölçütler KARARLAR K34'te, ölçümden önce yazıldı).

  python -m testseti.araclar.k34_kesme gelistirme   # geliştirme sayfalarındaki tespitler (bakmak için)
  python -m testseti.araclar.k34_kesme dogrulama    # doğrulama: etiket dosyası + yapay recall
  python -m testseti.araclar.k34_kesme sonuc        # etiketlendikten sonra isabet ve karar

Doğrulama sayfaları: TDE 10'un tamamı + diğer kitapların test sayfaları (K33 E7 ile aynı; yazım
modelinin de görmediği sayfalar). Geliştirme: diğer kitapların kalan sayfaları (test sayfası ±1 hariç).
Kural tespitleri ve modelin KURAL_DIGER önerileri karışık ve kaynağı gizli olarak etiketlenir.
"""

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
ETIKET = PROJE / "testseti" / "kesme_etiketler.json"
KAYNAK = PROJE / "veri" / "yazim_modeli" / "k34_kaynaklar.json"  # etiketlerken açılmaz
SONUC = PROJE / "testseti" / "kesme_olcum.json"


def kitaplar():
    from derskitabi.yazim_modeli.veri import DENEME_KITABI, EGITIM_KITAPLARI
    return [DENEME_KITABI] + EGITIM_KITAPLARI


def sayfa_secimi(kitap: str, dogrulama: bool):
    from derskitabi.yazim_modeli.veri import DENEME_KITABI, test_sayfalari
    haric = test_sayfalari().get(kitap, set())
    if kitap == DENEME_KITABI:
        return (lambda s: True) if dogrulama else (lambda s: False)
    if dogrulama:
        return lambda s: s in haric
    return lambda s: not any(abs(s - h) <= 1 for h in haric)


def kural_tespitleri(dogrulama: bool):
    from derskitabi.kayit import bloklari_yukle
    from derskitabi.kriterler import yazim
    for kitap in kitaplar():
        hepsi = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        sec = sayfa_secimi(kitap, dogrulama)
        secili = [b for b in hepsi if sec(b.sayfa_no)]
        if not secili:
            continue
        # ürünün yolu: yazim.analiz_et (satır birleştirme dahil); kesmeli adlar tüm kitaptan
        for t in yazim.analiz_et(secili, kitap_bloklari=hepsi):
            if t.alt_tur.endswith("kesme"):
                yield kitap, t, {(b.sayfa_no, b.blok_no): b for b in secili}


def yapay_recall() -> dict:
    """Doğrulama sayfalarındaki doğru "Ad’ek" yazımlarından kesme silinir; kural kaçını bulur?
    Kitaptaki kanıt sayısından silinen yazım düşülür (kendisi kendine kanıt olmasın)."""
    from derskitabi.kayit import bloklari_yukle
    from derskitabi.kriterler import kesme
    from derskitabi.model import Blok
    toplam = bulunan = 0
    for kitap in kitaplar():
        hepsi = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        kesmeli = kesme.kesmeli_adlar(hepsi)
        sec = sayfa_secimi(kitap, True)
        for b in hepsi:
            if not sec(b.sayfa_no) or b.tur not in ("paragraf", "kisa"):
                continue
            for m in kesme._KESMELI.finditer(b.metin):
                toplam += 1
                yeni = b.metin[:m.start()] + m.group(1) + m.group(2) + b.metin[m.end():]
                k = kesmeli.copy()
                k[m.group(1)] -= 1
                bb = Blok(b.sayfa_no, b.blok_no, b.bbox, yeni, b.basili_sayfa_no, b.tur)
                buldu = any(t.metin_parcasi == m.group(1) + m.group(2) for t in kesme.kesme_denetimi(bb, k))
                bulunan += buldu
    return {"toplam": toplam, "bulunan": bulunan, "recall": round(bulunan / max(1, toplam), 3)}


def model_onerileri(kural_kelimeleri: set) -> list[dict]:
    """Yazım modelinin (K33) doğrulama sayfalarında KURAL_DIGER dediği, kuralın bulmadığı kelimeler."""
    import torch  # noqa: F401 — pyarrow'dan önce
    from derskitabi.kayit import bloklari_yukle
    from derskitabi.yazim_modeli.etiketler import SINIFLAR
    from derskitabi.yazim_modeli.olc import ESIK, EN_IYI, Etiketleyici, metni_etiketle
    et = Etiketleyici(EN_IYI)
    sonuc = []
    for kitap in kitaplar():
        sec = sayfa_secimi(kitap, True)
        bloklar = [b for b in bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
                   if sec(b.sayfa_no) and b.tur in ("paragraf", "kisa")]
        for b, kel in zip(bloklar, metni_etiketle(et, [b.metin for b in bloklar])):
            for s, e, w, h, k in kel:
                sade = w.strip(".,;:!?\"'()“”‘’…")
                if h >= ESIK and SINIFLAR[k] == "KURAL_DIGER" and (kitap, b.sayfa_no, sade) not in kural_kelimeleri:
                    sonuc.append({"kitap": kitap, "sayfa_no": b.sayfa_no, "blok_no": b.blok_no, "kelime": sade,
                                  "baglam": b.metin[max(0, s - 80):e + 80]})
    return sonuc


def dogrulama() -> None:
    import torch  # noqa: F401 — Windows'ta pyarrow'dan önce yüklenmeli (K33)
    adaylar, kural_kelimeleri = [], set()
    for kitap, t, bloklar in kural_tespitleri(True):
        b = bloklar.get((t.sayfa_no, t.blok_no))
        metin = b.metin if b else ""
        i = metin.find(t.metin_parcasi)
        kural_kelimeleri.add((kitap, t.sayfa_no, t.metin_parcasi))
        adaylar.append({"kaynak": f"kural:{t.alt_tur}", "kitap": kitap, "sayfa_no": t.sayfa_no,
                        "blok_no": t.blok_no, "kelime": t.metin_parcasi,
                        "baglam": metin[max(0, i - 80):i + len(t.metin_parcasi) + 80], "aciklama": t.aciklama})
    print(f"Kural: {len(adaylar)} tespit {dict(Counter(a['kaynak'] for a in adaylar))}", flush=True)
    model = model_onerileri(kural_kelimeleri)
    print(f"Model (KURAL_DIGER, kuralın bulmadığı): {len(model)}", flush=True)
    for o in model:
        o.update(kaynak="model", aciklama="")
    hepsi = adaylar + model
    random.Random(34).shuffle(hepsi)
    etiket = [{"id": f"K34-{i + 1:03d}", **{k: v for k, v in o.items() if k not in ("kaynak", "aciklama")},
               "etiket": None, "not": ""} for i, o in enumerate(hepsi)]
    ETIKET.write_text(json.dumps(etiket, ensure_ascii=False, indent=1), encoding="utf-8")
    KAYNAK.write_text(json.dumps({e["id"]: o["kaynak"] for e, o in zip(etiket, hepsi)}, ensure_ascii=False),
                      encoding="utf-8")
    r = yapay_recall()
    print(f"Yapay recall: {r}")
    SONUC.write_text(json.dumps({"yapay_recall": r}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Etiketlenecek: {ETIKET.relative_to(PROJE)} ({len(etiket)})")


def sonuc() -> None:
    etiket = json.loads(ETIKET.read_text(encoding="utf-8"))
    kaynak = json.loads(KAYNAK.read_text(encoding="utf-8"))
    olcum = json.loads(SONUC.read_text(encoding="utf-8")) if SONUC.exists() else {}
    gruplar = Counter()
    for e in etiket:
        k = kaynak[e["id"]]
        for g in (k, "kural" if k.startswith("kural") else "model"):
            gruplar[(g, e["etiket"])] += 1
    ozet = {}
    for g in sorted({g for g, _ in gruplar}):
        gercek, sahte = gruplar[(g, "gercek")], gruplar[(g, "sahte")]
        ozet[g] = {"gercek": gercek, "sahte": sahte, "isabet": round(gercek / max(1, gercek + sahte), 3)}
    kural, model = ozet.get("kural", {}), ozet.get("model", {})
    karar = {"kural_girer": kural.get("isabet", 0) >= 0.70,
             "kural_orta_oncelik": 0.50 <= kural.get("isabet", 0) < 0.70,
             "model_girer": model.get("isabet", 0) >= 0.50 and model.get("gercek", 0) + model.get("sahte", 0) > 0}
    olcum.update(etiketli=ozet, karar=karar)
    SONUC.write_text(json.dumps(olcum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(olcum, ensure_ascii=False, indent=1))


def gelistirme() -> None:
    for kitap, t, bloklar in kural_tespitleri(False):
        b = bloklar.get((t.sayfa_no, t.blok_no))
        i = b.metin.find(t.metin_parcasi) if b else -1
        print(f"{kitap} s{t.sayfa_no} {t.alt_tur} «{t.metin_parcasi}» …"
              f"{(b.metin[max(0, i - 50):i + 50] if b else '')}…".replace("\n", " "))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"gelistirme": gelistirme, "dogrulama": dogrulama, "sonuc": sonuc}[sys.argv[1]]()
