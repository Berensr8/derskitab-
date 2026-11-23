"""K49: B katmanlarının seçimi, A paketi ve kilit dosyası (ön kayıt: testseti/k49_on_kayit.md).

- B1 (mevcut hat): A dışındaki bütün sayfalarda gösterilen (güven >= 0,5), sayfa okuma dışı benzersiz tespitler;
  80'den fazlaysa tohum 20261123 ile rastgele 80.
- B2 (sayfa okuma): aynı sayfalarda gösterilen sayfa_okuma tespitleri; 60'tan fazlaysa tohum "20261123:sayfa_okuma"
  ile rastgele 60.
- B3 (kurallar): K44'ün 9 kuralı + buyuk_harf_i + kesme_bosluk; B1'e girmemiş gösterilenler, kural başına en çok 10
  (tohum "20261123:<alt_tur>").
- A: 30 kilitli sayfa tek PDF'te (S01-S30 damgası); sistemin A sayfalarındaki çıktısı gizli saklanır.
- Kilit: testseti/bagimsiz4_kilit.txt, kurula gitmeden ÖNCE commit edilir.
"""
import datetime
import json
import random
import shutil
from collections import Counter

import pymupdf

from k42_katman import katman_farki, sayfa_glif_metni
from k49_ortak import (B1_SAYISI, B2_SAYISI, CIKTI, HAVUZ_SHA256, KITAP_AD, KITAPLAR, KURAL_BASINA, KURALLAR,
                       OLCULECEK_SURUM, PAKET, PROJE, TOHUM, havuz, ortam_kontrol, sha256_dosya_lf)

bilgi = ortam_kontrol(sert=False)
H = havuz()
PAKET.mkdir(exist_ok=True)
SO = "sayfa_okuma"


def anahtar(t: dict) -> tuple:
    return (t["sayfa_no"], t["blok_no"], t["metin_parcasi"], t["alt_tur"])


def sira(ka) -> tuple:
    k, a = ka
    return (k, a[0], a[1], a[2] or "", a[3] or "")


sistem = {k: json.loads((CIKTI / f"{k}_sistem.json").read_text(encoding="utf-8")) for k in KITAPLAR}

# A dışındaki sayfalarda benzersiz gösterilen tespitler
nesne: dict[tuple, dict] = {}
for k in KITAPLAR:
    b_sf = set(H["B_havuz"][k])
    for t in sistem[k]:
        if t["guven_skoru"] >= 0.5 and t["sayfa_no"] in b_sf and t["metin_parcasi"]:
            nesne.setdefault((k, anahtar(t)), t)
n1 = sorted((ka for ka in nesne if ka[1][3] != SO), key=sira)
n2 = sorted((ka for ka in nesne if ka[1][3] == SO), key=sira)


def ornekle(aday: list, n: int, tohum) -> list:
    return sorted(random.Random(tohum).sample(aday, n), key=sira) if len(aday) > n else list(aday)


b1 = ornekle(n1, B1_SAYISI, TOHUM)
b2 = ornekle(n2, B2_SAYISI, f"{TOHUM}:{SO}")
secilen: dict[tuple, list[str]] = {}
for ka in b1:
    secilen.setdefault(ka, []).append("B1")
for ka in b2:
    secilen.setdefault(ka, []).append("B2")
kural_ozet = {}
for alt in KURALLAR:
    havuzda = [ka for ka in n1 if ka[1][3] == alt]
    aday = [ka for ka in havuzda if ka not in b1]
    ornek = ornekle(aday, KURAL_BASINA, f"{TOHUM}:{alt}")
    kural_ozet[alt] = {"havuzda": len(havuzda), "B1_icinde": len(havuzda) - len(aday), "B3_eklenen": len(ornek)}
    for ka in ornek:
        secilen.setdefault(ka, []).append(f"B3:{alt}")

# ---------------------------------------------------------------- bağlam + metin katmanı kontrolü
bloklar = {k: {(b["sayfa_no"], b["blok_no"]): b for b in
               json.loads((PROJE / "veri" / f"{k}_bloklar.json").read_text(encoding="utf-8"))} for k in KITAPLAR}
pdfler = {k: pymupdf.open(PROJE / "veri" / f"{k}.pdf") for k in KITAPLAR}
glif_onbellek: dict[tuple, str] = {}


def glif(k, s):
    if (k, s) not in glif_onbellek:
        glif_onbellek[(k, s)] = sayfa_glif_metni(pdfler[k][s - 1])
    return glif_onbellek[(k, s)]


B = []
for (k, a), katman in secilen.items():
    t = nesne[(k, a)]
    m = " ".join(bloklar[k].get((t["sayfa_no"], t["blok_no"]), {"metin": ""})["metin"].split())
    p = " ".join(t["metin_parcasi"].split())
    i = m.find(p)
    bas, son = (max(0, i - 110), min(len(m), i + len(p) + 110)) if i >= 0 else (0, 240)
    B.append({
        "kitap": k, "sayfa_no": t["sayfa_no"], "basili": t["basili_sayfa_no"], "blok_no": t["blok_no"],
        "parca": t["metin_parcasi"],
        "baglam": ("…" if bas else "") + m[bas:son] + ("…" if son < len(m) else ""),
        "katman": katman,
        "katman_farki": katman_farki(glif(k, t["sayfa_no"]), t["metin_parcasi"]),
        "gizli": {"alt_tur": t["alt_tur"], "aciklama": t["aciklama"], "guven": t["guven_skoru"]},
    })
B.sort(key=lambda x: (x["kitap"], x["sayfa_no"], x["blok_no"], x["parca"], x["gizli"]["alt_tur"] or ""))
random.Random(TOHUM).shuffle(B)
for n, x in enumerate(B, 1):
    x["no"] = f"B{n:03d}"
(CIKTI / "B_anahtar.json").write_text(json.dumps(B, ensure_ascii=False, indent=1), encoding="utf-8")
(CIKTI / "B_nufus.json").write_text(json.dumps(
    {"N1": len(n1), "N2": len(n2), "N1_kitap": {k: sum(ka[0] == k for ka in n1) for k in KITAPLAR},
     "N2_kitap": {k: sum(ka[0] == k for ka in n2) for k in KITAPLAR}, "kurallar": kural_ozet},
    ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------------------------------------------------------- A paketi
A = [(k, s, f"S{i:02d}") for i, (k, s) in enumerate([(k, s) for k in KITAPLAR for s in sorted(H["A"][k])], 1)]
birlesik = pymupdf.open()
metin = []
for k, s, kod in A:
    birlesik.insert_pdf(pdfler[k], from_page=s - 1, to_page=s - 1)
    metin.append(f"===== {kod} | {KITAP_AD[k]}, PDF s.{s} =====\n" + pdfler[k][s - 1].get_text())
    birlesik[-1].insert_text((20, 18), f"{kod}  |  {KITAP_AD[k]}, PDF s.{s}", fontsize=11,
                             color=(0.64, 0.14, 0.1), fontname="helv")
birlesik.save(PAKET / "A_30_sayfa.pdf", garbage=3, deflate=True)
(PAKET / "A_30_sayfa_metin.txt").write_text("\n\n".join(metin), encoding="utf-8")
(PAKET / "A_sayfa_listesi.json").write_text(
    json.dumps([{"kod": kod, "kitap": k, "sayfa_no": s} for k, s, kod in A], ensure_ascii=False, indent=1),
    encoding="utf-8")
shutil.copyfile(PROJE / "testseti" / "bagimsiz" / "A_talimat.txt", PAKET / "A_talimat.txt")
gizli = [{"sayfa": kod, "kitap": k, "sayfa_no": s, "sistem": [t for t in sistem[k] if t["sayfa_no"] == s]}
         for k, s, kod in A]
(CIKTI / "A_sistem_gizli.json").write_text(json.dumps(gizli, ensure_ascii=False, indent=1, default=list),
                                           encoding="utf-8")

# ---------------------------------------------------------------- özet (A çıktısı kasıtlı olarak yazdırılmaz)
print(f"B havuzu gösterilen: mevcut hat N1={len(n1)}, sayfa okuma N2={len(n2)}")
print(f"B1 {len(b1)}, B2 {len(b2)}, B3 {sum(v['B3_eklenen'] for v in kural_ozet.values())}; "
      f"toplam benzersiz B adayı {len(B)}; katman farkı {sum(bool(x['katman_farki']) for x in B)}")
print("B1 alt_tur:", dict(Counter(nesne[ka]["alt_tur"] for ka in b1)))
for alt, v in kural_ozet.items():
    if v["havuzda"]:
        print(f"  kural {alt}: {v}")
for x in B:
    if x["katman_farki"]:
        print("  KATMAN FARKI:", x["no"], x["kitap"], x["sayfa_no"], x["katman"], x["parca"][:60], "->", x["katman_farki"])
print("A sayfa sayısı:", len(A), "| gizli çıktı yazıldı (içeriği yazdırılmadı)")

# ---------------------------------------------------------------- kilit dosyası
dosyalar = [("havuz.json", CIKTI / "havuz.json"), ("B_anahtar.json", CIKTI / "B_anahtar.json"),
            ("B_nufus.json", CIKTI / "B_nufus.json"), ("A_sistem_gizli.json", CIKTI / "A_sistem_gizli.json")]
for k in KITAPLAR:
    dosyalar += [(f"{k}_sistem.json", CIKTI / f"{k}_sistem.json"), (f"{k}_sayac.json", CIKTI / f"{k}_sayac.json")]
satir = [f"{sha256_dosya_lf(y)} *{ad_}" for ad_, y in dosyalar]
kilit = f"""Bağımsız değerlendirme 4 (K49) kilidi — {datetime.datetime.now():%Y-%m-%d %H:%M}
Sistemin kilitli A sayfalarındaki ve B örneklemindeki çıktısı, yapay zekâlar kararlarını vermeden ÖNCE hesaplandı.
Dosyalar veri/bagimsiz4/ altında (git dışı). Parmak izleri SHA-256; satır sonları LF'ye çevrilerek hesaplandı:
{chr(10).join(satir)}
Ön kayıt: testseti/k49_on_kayit.md (havuz.json SHA-256 {HAVUZ_SHA256}; tohum {TOHUM}).
Ölçülen kod: {OLCULECEK_SURUM} (betiklerin commit'i: {bilgi['commit'][:7]}; derskitabi/ {OLCULECEK_SURUM} ile birebir aynı).
Ortam: .venv Python, PyMuPDF {bilgi['pymupdf']}; Ollama gemma4:12b-it-qat (yazım hakemi ve sayfa okuma).
Yapılandırma: ürünün varsayılanı (yazım hakemi açık, sayfa okuma açık); testseti/araclar/k49_sistem.py (zincir arayuz/hat.py ile aynı).
B havuzu (A dışındaki 478 sayfa) gösterilen: mevcut hat N1 = {len(n1)}, sayfa okuma N2 = {len(n2)}.
B1 = {len(b1)} (mevcut hat örneği), B2 = {len(b2)} (sayfa okuma örneği), B3 = {sum(v['B3_eklenen'] for v in kural_ozet.values())} (kurallar, kural başına en çok {KURAL_BASINA}).
Toplam benzersiz B adayı {len(B)}; metin katmanı farkı {sum(bool(x['katman_farki']) for x in B)} (kurula gitmez, ayrı raporlanır).
A: 30 kilitli sayfa (S01-S15 Tarih 9, S16-S30 Coğrafya 9). A_talimat.txt K39/K42/K45 ile aynı.
"""
(PROJE / "testseti" / "bagimsiz4_kilit.txt").write_text(kilit, encoding="utf-8")
print("Kilit dosyası yazıldı: testseti/bagimsiz4_kilit.txt")
