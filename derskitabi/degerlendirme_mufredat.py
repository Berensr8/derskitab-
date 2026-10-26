"""Değerlendirme: müfredat uyumu (K31). Ölçüt sonuçtan önce KARARLAR.md'de sabitlendi.

  - Pozitif : kitabın kendi sınıfının ve kapsadığı temaların çıktıları → "karşılanıyor/kısmen" beklenir.
  - Negatif : aynı dersin başka sınıflarının çıktıları ve aynı sınıfın kitapta olmayan temaları (Sosyal
              Bilgiler 6 "1. Kitap": SB.6.4–6.6 ikinci kitapta) → "karşılanmıyor" beklenir.
  - Eksik tema: Biyoloji 9'dan 2. temanın sayfaları çıkarılır; o temanın çıktıları "karşılanmıyor"a dönmeli.
  - Konum : karşılanan pozitif çıktıda en benzer paragrafın sayfası çıktının temasında mı?
  - Temiz doğrulama (K31 eki): ilk ölçümden sonra düzeltme yapıldığı için (tanıtım sayfaları) karar, hiç
    kullanılmamış Biyoloji 11 üzerindeki aynı ölçütlerle verilir; eksik tema testi orada da yapılır.

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
DOGRULAMA = {"biyoloji11": ("biyoloji", 11, (1, 2))}  # K31 eki: düzeltmeden sonra ilk kez çalıştırılır
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
        return _kapaklar_sonraki_temaya(sonuc, bloklar, set(sonuc))
    isaret = {}
    for b in bloklar:
        if (m := _TEMA_BASLIGI.match(b.metin)) and len(b.metin) < 40 and b.sayfa_no > ICINDEKILER_SONU:
            isaret.setdefault(b.sayfa_no, int(m.group(1)))
    # Sayfa başlığı her sayfada yok: başlıksız sayfa son görülen temaya aittir
    sonuc, tema = {}, None
    for no in range(min(isaret), max(b.sayfa_no for b in bloklar) + 1):
        tema = isaret.get(no, tema)
        sonuc[no] = tema
    return _kapaklar_sonraki_temaya(sonuc, bloklar, set(isaret))


def _kapaklar_sonraki_temaya(sonuc: dict[int, int], bloklar, kesin) -> dict[int, int]:
    """Tema kapağı ve sunusu, açtığı temaya aittir (sayfa başlığı kapakta yok, ileri doğru doldurma kapağı
    önceki temaya veriyordu). kesin: teması kesin bilinen sayfalar (başlıklı ya da içindekilerden)."""
    tanitim = mufredat.tanitim_sayfalari(bloklar)
    for kapak in sorted(p for p in tanitim if p > ICINDEKILER_SONU):
        sonraki = min((p for p in kesin if p > kapak and p not in tanitim), default=None)
        if sonraki is not None:
            for p in range(kapak, sonraki):
                sonuc[p] = sonuc[sonraki]
    return sonuc


def calistir(kitap: str, bloklar, ciktilar, onbellek) -> list[dict]:
    try:
        kayit, _ = mufredat.analiz_et(bloklar, ciktilar, onbellek=onbellek, ilerleme=lambda m: print(m, flush=True))
    finally:
        json_kaydet(onbellek, ONBELLEK)
    return kayit


def kitap_olc(kitap, program, sinif, temalar, ciktilar, onbellek) -> tuple[dict, Counter]:
    bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
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
    print(f"  pozitif kapsam {poz_iyi}/{poz}, negatifte 'karşılanıyor' {neg_kotu}/{neg}, "
          f"konum {sonuc[('konum', True)]}/{poz_iyi}", flush=True)
    sonuc_k = {"sayim": {f"{g}/{k}": v for (g, k), v in sonuc.items()},
               "pozitif_kapsam": round(poz_iyi / poz, 3), "negatif_karsilaniyor": round(neg_kotu / neg, 3),
               "konum": round(sonuc[("konum", True)] / max(1, poz_iyi), 3), "kayit": kayit}
    return sonuc_k, Counter({"poz": poz, "poz_iyi": poz_iyi, "neg": neg, "neg_kotu": neg_kotu,
                             "konum": sonuc[("konum", True)]})


def eksik_tema_olc(kitap, sinif, ciktilar, onbellek, cikan_tema=2) -> dict:
    """Kitaptan bir temanın sayfaları (kapağıyla) çıkarılır; o temanın çıktıları "karşılanmıyor"a dönmeli."""
    bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
    temalar_s = sayfa_temalari(kitap, bloklar)
    eksik = [b for b in bloklar if temalar_s.get(b.sayfa_no) != cikan_tema]
    ciktilar = [c for c in ciktilar if c.sinif == sinif]
    print(f"## Eksik tema testi: {kitap}'dan {len(bloklar) - len(eksik)} blok ({cikan_tema}. tema) çıkarıldı", flush=True)
    kayit = calistir(f"{kitap}_eksik", eksik, ciktilar, onbellek)
    et = Counter((r["tema"], r["karar"]) for r in kayit)
    cikan = sum(v for (t, k), v in et.items() if t == cikan_tema)
    kalan = sum(v for (t, k), v in et.items() if t != cikan_tema)
    kalan_iyi = sum(v for (t, k), v in et.items() if t != cikan_tema and k in ("karsilaniyor", "kismen"))
    sonuc = {"cikan_tema_karsilanmiyor": f"{et[(cikan_tema, 'karsilanmiyor')]}/{cikan}",
             "kalan_karsilaniyor_kismen": f"{kalan_iyi}/{kalan}",
             "gecti": et[(cikan_tema, "karsilanmiyor")] >= 0.8 * cikan and kalan_iyi >= 0.8 * kalan, "kayit": kayit}
    print("  ", {k: v for k, v in sonuc.items() if k != "kayit"}, flush=True)
    return sonuc


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    onbellek = json.loads(ONBELLEK.read_text(encoding="utf-8")) if ONBELLEK.exists() else {}
    programlar = {ad: mufredat.program_ciktilari(PROJE / "veri" / "programlar" / f"{ad}_programi.pdf")
                  for ad in {p for p, _, _ in (KITAPLAR | DOGRULAMA).values()}}
    rapor = {}
    for ad, kume in (("gelistirme", KITAPLAR), ("dogrulama", DOGRULAMA)):
        bolum, toplam = {"kitaplar": {}}, Counter()
        for kitap, (program, sinif, temalar) in kume.items():
            bolum["kitaplar"][kitap], sayim = kitap_olc(kitap, program, sinif, temalar, programlar[program], onbellek)
            toplam.update(sayim)
        kitap, (program, sinif, _) = next(iter(kume.items()))
        bolum["eksik_tema"] = eksik_tema_olc(kitap, sinif, programlar[program], onbellek)
        bolum["genel"] = {"pozitif_kapsam": round(toplam["poz_iyi"] / toplam["poz"], 3),
                          "negatif_karsilaniyor": round(toplam["neg_kotu"] / toplam["neg"], 3),
                          "konum": round(toplam["konum"] / max(1, toplam["poz_iyi"]), 3)}
        bolum["karar_kurali_gecti"] = (bolum["genel"]["pozitif_kapsam"] >= 0.85
                                       and bolum["genel"]["negatif_karsilaniyor"] <= 0.30 and bolum["eksik_tema"]["gecti"])
        print(f"Genel ({ad}):", bolum["genel"], "| karar kuralı:", bolum["karar_kurali_gecti"], flush=True)
        rapor[ad] = bolum
    json_kaydet(rapor, PROJE / "veri" / "degerlendirme_mufredat.json")


if __name__ == "__main__":
    main()
