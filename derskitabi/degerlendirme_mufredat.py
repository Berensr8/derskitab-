"""Değerlendirme: müfredat uyumu (K31). Ölçüt sonuçtan önce KARARLAR.md'de sabitlendi.

  - Pozitif : kitabın kendi sınıfının ve kapsadığı temaların çıktıları → "karşılanıyor/kısmen" beklenir.
  - Negatif : aynı dersin başka sınıflarının çıktıları ve aynı sınıfın kitapta olmayan temaları (Sosyal
              Bilgiler 6 "1. Kitap": SB.6.4–6.6 ikinci kitapta) → "karşılanmıyor" beklenir.
  - Eksik tema: Biyoloji 9'dan 2. temanın sayfaları çıkarılır; o temanın çıktıları "karşılanmıyor"a dönmeli.
  - Konum : karşılanan pozitif çıktıda en benzer paragrafın sayfası çıktının temasında mı?

Kullanım:
    python -m derskitabi.degerlendirme_mufredat
"""

import json
import re
import sys
from collections import Counter

from .degerlendirme import PROJE
from .kayit import bloklari_yukle, json_kaydet
from .kriterler import mufredat

# kitap: (program, sınıf, kitabın kapsadığı temalar)
KITAPLAR = {"biyoloji9": ("biyoloji", 9, (1, 2)), "biyoloji10": ("biyoloji", 10, (1, 2)),
            "kitap": ("sosyal", 6, (1, 2, 3))}
# Sosyal Bilgiler 6 içindekiler sayfası (basılı sayfa): öğrenme alanlarının aralıkları
SOSYAL6_ALANLAR = {1: (12, 53), 2: (54, 107), 3: (108, 179)}
_TEMA_BASLIGI = re.compile(r"^\s*(\d)\.\s*Tema\b")
ICINDEKILER_SONU = 12  # Biyoloji kitaplarında ilk sayfalar içindekiler ve tanıtım ("1. Tema … 14")
ONBELLEK = PROJE / "veri" / "mufredat_onbellek.json"


def sayfa_temalari(kitap: str, bloklar) -> dict[int, int]:
    """{PDF sayfası: tema} — Biyoloji'de sayfa başlığından ("1. Tema / ENERJİ"), Sosyal 6'da içindekilerden."""
    if kitap == "kitap":
        sonuc = {}
        for b in bloklar:
            if b.basili_sayfa_no and b.basili_sayfa_no.isdigit():
                no = int(b.basili_sayfa_no)
                for alan, (a, z) in SOSYAL6_ALANLAR.items():
                    if a <= no <= z:
                        sonuc[b.sayfa_no] = alan
        return sonuc
    isaret = {}
    for b in bloklar:
        if (m := _TEMA_BASLIGI.match(b.metin)) and len(b.metin) < 40 and b.sayfa_no > ICINDEKILER_SONU:
            isaret.setdefault(b.sayfa_no, int(m.group(1)))
    # Sayfa başlığı her sayfada yok: başlıksız sayfa son görülen temaya aittir
    sonuc, tema = {}, None
    for no in range(min(isaret), max(b.sayfa_no for b in bloklar) + 1):
        tema = isaret.get(no, tema)
        sonuc[no] = tema
    return sonuc


def calistir(kitap: str, bloklar, ciktilar, onbellek) -> list[dict]:
    try:
        kayit, _ = mufredat.analiz_et(bloklar, ciktilar, onbellek=onbellek, ilerleme=lambda m: print(m, flush=True))
    finally:
        json_kaydet(onbellek, ONBELLEK)
    return kayit


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    onbellek = json.loads(ONBELLEK.read_text(encoding="utf-8")) if ONBELLEK.exists() else {}
    programlar = {ad: mufredat.program_ciktilari(PROJE / "veri" / "programlar" / f"{ad}_programi.pdf")
                  for ad in {p for p, _, _ in KITAPLAR.values()}}
    rapor = {"kitaplar": {}}
    toplam = Counter()
    for kitap, (program, sinif, temalar) in KITAPLAR.items():
        bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        ciktilar = programlar[program]
        pozitif = {c.kod for c in ciktilar if c.sinif == sinif and c.tema in temalar}
        print(f"## {kitap}: {len(pozitif)} pozitif, {len(ciktilar) - len(pozitif)} negatif çıktı", flush=True)
        kayit = calistir(kitap, bloklar, ciktilar, onbellek)
        temalar_s = sayfa_temalari(kitap, bloklar)
        sonuc = Counter()
        for r in kayit:
            grup = "pozitif" if r["kod"] in pozitif else ("negatif_ayni_sinif" if r["sinif"] == sinif else "negatif")
            sonuc[(grup, r["karar"])] += 1
            if grup == "pozitif" and r["karar"] in ("karsilaniyor", "kismen"):
                sonuc[("konum", temalar_s.get(r["sayfalar"][0]) == r["tema"])] += 1
        poz = sum(v for (g, k), v in sonuc.items() if g == "pozitif")
        poz_iyi = sonuc[("pozitif", "karsilaniyor")] + sonuc[("pozitif", "kismen")]
        neg = sum(v for (g, k), v in sonuc.items() if g.startswith("negatif"))
        neg_kotu = sonuc[("negatif", "karsilaniyor")] + sonuc[("negatif_ayni_sinif", "karsilaniyor")]
        rapor["kitaplar"][kitap] = {"sayim": {f"{g}/{k}": v for (g, k), v in sonuc.items()},
                                    "pozitif_kapsam": round(poz_iyi / poz, 3), "negatif_karsilaniyor": round(neg_kotu / neg, 3),
                                    "konum": round(sonuc[("konum", True)] / max(1, poz_iyi), 3),
                                    "kayit": kayit}
        toplam.update({"poz": poz, "poz_iyi": poz_iyi, "neg": neg, "neg_kotu": neg_kotu})
        print(f"  pozitif kapsam {poz_iyi}/{poz}, negatifte 'karşılanıyor' {neg_kotu}/{neg}, "
              f"konum {sonuc[('konum', True)]}/{poz_iyi}", flush=True)

    # Eksik tema testi: Biyoloji 9'dan 2. tema çıkarılır
    bloklar = bloklari_yukle(PROJE / "veri" / "biyoloji9_bloklar.json")
    temalar_s = sayfa_temalari("biyoloji9", bloklar)
    eksik = [b for b in bloklar if temalar_s.get(b.sayfa_no) != 2]
    ciktilar = [c for c in programlar["biyoloji"] if c.sinif == 9]
    print(f"## Eksik tema testi: Biyoloji 9'dan {len(bloklar) - len(eksik)} blok (2. tema) çıkarıldı", flush=True)
    kayit = calistir("biyoloji9_eksik", eksik, ciktilar, onbellek)
    et = Counter((r["tema"], r["karar"]) for r in kayit)
    t2 = sum(v for (t, k), v in et.items() if t == 2)
    t1 = sum(v for (t, k), v in et.items() if t == 1)
    rapor["eksik_tema"] = {"tema2_karsilanmiyor": f"{et[(2, 'karsilanmiyor')]}/{t2}",
                           "tema1_karsilaniyor_kismen": f"{et[(1, 'karsilaniyor')] + et[(1, 'kismen')]}/{t1}",
                           "kayit": kayit}
    rapor["genel"] = {"pozitif_kapsam": round(toplam["poz_iyi"] / toplam["poz"], 3),
                      "negatif_karsilaniyor": round(toplam["neg_kotu"] / toplam["neg"], 3)}
    json_kaydet(rapor, PROJE / "veri" / "degerlendirme_mufredat.json")
    print("Genel:", rapor["genel"], "| Eksik tema:", {k: v for k, v in rapor["eksik_tema"].items() if k != "kayit"})


if __name__ == "__main__":
    main()
