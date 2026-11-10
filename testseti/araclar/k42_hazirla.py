"""K42 adım 3-4: B seçimi, A paketi ve kilit dosyası (ön kayıt: testseti/k42_on_kayit.md).

- B (isabet): kitap başına 8, toplam 40 rastgele gösterilen (güven >= 0,5) tespit; ek olarak K41'de
  eklenen her yeni kural (alt_tur) için havuzda varsa en çok 10 tespit. Tohum 20261110.
  Ana sonuç ürünün varsayılanı olan hakemli çıktıdan; hakemsiz çıktı ikincil olarak ayrıca işaretlenir.
- A (bulma oranı): 30 kilitli sayfa tek PDF'te, her sayfanın üstünde S01-S30 damgası; sistemin A
  sayfalarındaki çıktısı gizli saklanır (kurul sonuçlanana dek bakılmaz).
- Kilit: testseti/bagimsiz2_kilit.txt (parmak izleri), kurula gitmeden ÖNCE commit edilir.
"""
import json
import random
import shutil
import sys
from collections import Counter

import pymupdf

from k42_ortak import (CIKTI, HAVUZ_SHA256, KITAP_AD, KITAPLAR, OLCULECEK_SURUM, PAKET, PROJE, YENI_KURALLAR,
                       _git, havuz, ortam_kontrol, sha256_dosya_lf)
from k42_katman import katman_farki, sayfa_glif_metni

TOHUM = 20261110
bilgi = ortam_kontrol(sert=False)
H = havuz()
PAKET.mkdir(exist_ok=True)


def yukle(kitap: str, tur: str) -> list[dict]:
    return json.loads((CIKTI / f"{kitap}_sistem_{tur}.json").read_text(encoding="utf-8"))


def anahtar(t: dict) -> tuple:
    return (t["sayfa_no"], t["blok_no"], t["metin_parcasi"], t["alt_tur"])


def sirala(liste: list[dict]) -> list[dict]:
    return sorted(liste, key=lambda t: (t["sayfa_no"], t["blok_no"], t["metin_parcasi"] or "", t["alt_tur"] or ""))


# ---------------------------------------------------------------- B listesi (ön kayıttan sapma: örnekleme yok)
# Ön kayıt "kitap başına 8, toplam 40 gösterilen tespit" diyordu; kilitli B havuzunda hakemli çıktıda yalnız 25
# gösterilen tespit çıktığı için bu şart sağlanamadı. Karar (Beren, 2026-11-10): havuzdaki gösterilen
# tespitlerin HEPSİ alınır (hakemli 25 ana, hakemsiz 30 ikincil; ortak olanlar bir kez sunulur), havuza sayfa eklenmez.
hakemli = {k: yukle(k, "hakemli") for k in KITAPLAR}
hakemsiz = {k: yukle(k, "hakemsiz") for k in KITAPLAR}
hakemli_guven = {k: {anahtar(t): t["guven_skoru"] for t in hakemli[k]} for k in KITAPLAR}
hakemsiz_guven = {k: {anahtar(t): t["guven_skoru"] for t in hakemsiz[k]} for k in KITAPLAR}
hakemli_t = {k: {anahtar(t): t for t in hakemli[k]} for k in KITAPLAR}
hakemsiz_t = {k: {anahtar(t): t for t in hakemsiz[k]} for k in KITAPLAR}

secilenler: dict[tuple, dict] = {}  # (kitap, anahtar) -> {"kitap", "t", "kaynak"}
for k in KITAPLAR:
    b_sf = set(H["B_havuz"][k])
    for tur, liste in (("hakemli", hakemli[k]), ("hakemsiz", hakemsiz[k])):
        for t in sirala([t for t in liste if t["guven_skoru"] >= 0.5 and t["sayfa_no"] in b_sf and t["metin_parcasi"]]):
            e = secilenler.setdefault((k, anahtar(t)), {"kitap": k, "t": hakemli_t[k].get(anahtar(t), t), "kaynak": []})
            e["kaynak"].append(tur)

# Yeni kurallar: ön kayıttaki gibi kural başına en çok 10 (örnekleme yalnız 10'dan fazlaysa; hepsi kurula gider)
yeni_secim = {}
for alt in YENI_KURALLAR:
    aday = sorted([(k, a) for (k, a), e in secilenler.items() if e["t"]["alt_tur"] == alt],
                  key=lambda ka: (ka[0], ka[1][0], ka[1][1], ka[1][2] or ""))
    rr = random.Random(f"{TOHUM}:{alt}")
    ornek = rr.sample(aday, 10) if len(aday) > 10 else aday
    yeni_secim[alt] = {"havuzda": len(aday), "ornek": [list(map(str, (k, *a))) for k, a in ornek]}
    for ka in ornek:
        secilenler[ka]["kaynak"].append(f"yeni:{alt}")


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
for (k, a), e in secilenler.items():
    t = e["t"]
    m = " ".join(bloklar[k].get((t["sayfa_no"], t["blok_no"]), {"metin": ""})["metin"].split())
    i = m.find(t["metin_parcasi"])
    bas, son = (max(0, i - 110), min(len(m), i + len(t["metin_parcasi"]) + 110)) if i >= 0 else (0, 240)
    baglam = ("…" if bas else "") + m[bas:son] + ("…" if son < len(m) else "")
    B.append({"kitap": k, "sayfa_no": t["sayfa_no"], "basili": t["basili_sayfa_no"], "blok_no": t["blok_no"],
              "parca": t["metin_parcasi"], "baglam": baglam, "kaynak": e["kaynak"],
              "katman_farki": katman_farki(glif(k, t["sayfa_no"]), t["metin_parcasi"]),
              "gizli": {"alt_tur": t["alt_tur"], "aciklama": t["aciklama"],
                        "hakemli_gosterilen": "hakemli" in e["kaynak"], "guven_hakemli": hakemli_guven[k].get(anahtar(t)),
                        "hakemsiz_gosterilen": "hakemsiz" in e["kaynak"], "guven_hakemsiz": hakemsiz_guven[k].get(anahtar(t))}})
B.sort(key=lambda x: (x["kitap"], x["sayfa_no"], x["blok_no"], x["parca"]))
random.Random(TOHUM).shuffle(B)
for n, x in enumerate(B, 1):
    x["no"] = f"B{n:02d}"
(CIKTI / "B_anahtar.json").write_text(json.dumps(B, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------------------------------------------------------- A paketi
A = [(k, s, f"S{i:02d}") for i, (k, s) in enumerate(
    [(k, s) for k in ("biyoloji9", "biyoloji11", "turkdili10") for s in sorted(H["A"][k])], 1)]
birlesik = pymupdf.open()
metin = []
kisa = {"biyoloji9": "Biyoloji 9", "biyoloji11": "Biyoloji 11", "turkdili10": "TDE 10"}
ad = {"biyoloji9": "Biyoloji 9", "biyoloji11": "Biyoloji 11", "turkdili10": "Türk Dili ve Edebiyatı 10"}
for k, s, kod in A:
    birlesik.insert_pdf(pdfler[k], from_page=s - 1, to_page=s - 1)
    metin.append(f"===== {kod} | {ad[k]}, PDF s.{s} =====\n" + pdfler[k][s - 1].get_text())
    birlesik[-1].insert_text((20, 18), f"{kod}  |  {kisa[k]}, PDF s.{s}", fontsize=11, color=(0.64, 0.14, 0.1), fontname="helv")
birlesik.save(PAKET / "A_30_sayfa.pdf", garbage=3, deflate=True)
(PAKET / "A_30_sayfa_metin.txt").write_text("\n\n".join(metin), encoding="utf-8")
(PAKET / "A_sayfa_listesi.json").write_text(
    json.dumps([{"kod": kod, "kitap": k, "sayfa_no": s} for k, s, kod in A], ensure_ascii=False, indent=1), encoding="utf-8")
shutil.copyfile(PROJE / "bagimsiz_degerlendirme" / "A_talimat.txt", PAKET / "A_talimat.txt")  # K39'un aynısı

gizli = []
for k, s, kod in A:
    gizli.append({"sayfa": kod, "kitap": k, "sayfa_no": s,
                  "hakemli": [t for t in hakemli[k] if t["sayfa_no"] == s],
                  "hakemsiz": [t for t in hakemsiz[k] if t["sayfa_no"] == s]})
(CIKTI / "A_sistem_gizli.json").write_text(json.dumps(gizli, ensure_ascii=False, indent=1, default=list), encoding="utf-8")

# ---------------------------------------------------------------- özet (A çıktısı kasıtlı olarak yazdırılmaz)
print("B toplam (birleşim):", len(B), "| hakemli gösterilen:", sum("hakemli" in x["kaynak"] for x in B),
      "| hakemsiz gösterilen:", sum("hakemsiz" in x["kaynak"] for x in B),
      "| ikisinde de:", sum("hakemli" in x["kaynak"] and "hakemsiz" in x["kaynak"] for x in B),
      "| katman farkı:", sum(bool(x["katman_farki"]) for x in B))
print("B alt_tur dağılımı (birleşim):", dict(Counter(x["gizli"]["alt_tur"] for x in B)))
for k in KITAPLAR:
    print(f"  {k}: hakemli {sum(1 for x in B if x['kitap'] == k and 'hakemli' in x['kaynak'])}, "
          f"hakemsiz {sum(1 for x in B if x['kitap'] == k and 'hakemsiz' in x['kaynak'])}")
for alt, v in yeni_secim.items():
    print(f"  yeni kural {alt}: havuzda {v['havuzda']}, örnek {len(v['ornek'])}")
for x in B:
    if x["katman_farki"]:
        print("  KATMAN FARKI:", x["no"], x["kitap"], x["sayfa_no"], x["parca"], "->", x["katman_farki"])
print("A sayfa sayısı:", len(A), "| gizli çıktı yazıldı (içeriği yazdırılmadı)")

# ---------------------------------------------------------------- kilit dosyası
dosyalar = [("havuz.json", CIKTI / "havuz.json"), ("B_anahtar.json", CIKTI / "B_anahtar.json"),
            ("A_sistem_gizli.json", CIKTI / "A_sistem_gizli.json")]
for k in KITAPLAR:
    for tur in ("hakemsiz", "hakemli"):
        dosyalar.append((f"{k}_sistem_{tur}.json", CIKTI / f"{k}_sistem_{tur}.json"))
satir = [f"{sha256_dosya_lf(y)} *{ad_}" for ad_, y in dosyalar]
import datetime
kilit = f"""Bağımsız değerlendirme 2 (K42) kilidi — {datetime.datetime.now():%Y-%m-%d %H:%M}
Sistemin kilitli A sayfalarındaki ve B örnekleminden seçilen tespitlerdeki çıktısı, yapay zekâlar kararlarını vermeden ÖNCE hesaplandı.
Dosyalar veri/bagimsiz2/ altında (git dışı). Parmak izleri SHA-256; satır sonları LF'ye çevrilerek hesaplandı (Windows CRLF yazar):
{chr(10).join(satir)}
Ön kayıt: testseti/k42_on_kayit.md (havuz.json SHA-256 {HAVUZ_SHA256}; tohum {TOHUM}).
Ölçülen kod: {OLCULECEK_SURUM} (ölçüm betiklerinin commit'i: {bilgi['commit'][:7]}; derskitabi/ klasörü {OLCULECEK_SURUM} ile birebir aynı, çalışma ağacı temiz).
Ortam: .venv Python, PyMuPDF {bilgi['pymupdf']}.
Yapılandırma: ürünün varsayılanı. Yazım hakemi varsayılan olarak açık (Ollama + gemma4:12b-it-qat hazır). Ana sonuç hakemli çıktıdır; hakemsiz çıktı ikincil olarak ayrıca hesaplandı.
  Hakem her tespit için bağımsız olduğundan yalnız ölçüm sayfalarındaki tespitlere uygulandı (sonuç tüm kitaba uygulamayla aynıdır).
B seçimi — ÖN KAYITTAN SAPMA: Ön kayıt "kitap başına 8, toplam 40 gösterilen tespit" diyordu. Kilitli B havuzunda (200 sayfa) hakemli çıktıda
  yalnız {sum("hakemli" in x["kaynak"] for x in B)} gösterilen (güven >= 0,5) tespit çıktığından (hakem kelime tespitlerinin çoğunu düşük önceliğe indirdi)
  bu şart sağlanamadı. Karar (Beren, 2026-11-10): örnekleme yapılmadı; havuzdaki gösterilen tespitlerin HEPSİ alındı. Havuza sayfa eklenmedi.
  Ana sonuç hakemli ({sum("hakemli" in x["kaynak"] for x in B)} tespit), ikincil hakemsiz ({sum("hakemsiz" in x["kaynak"] for x in B)} tespit);
  ikisinde de olan tespit kurula bir kez sunulur; isabet iki sistem için ayrı hesaplanır, birleşik oran verilmez.
  Yeni kurallar (buyuk_harf_i, dizgi_rakam_harf, duzeltme_isareti_nispet, noktalama_cift_tek_tirnak, noktalama_parantez_cift_nokta,
  noktalama_ters_tirnak) için ön kayıttaki gibi kural başına en çok 10 tespit raporlanır (10'dan fazlaysa tohum "{TOHUM}:<alt_tur>" ile örneklem; hepsi kurula gider).
Metin katmanı kontrolü (ön kayıt eki, K41-ek): adayın her sözcüğü sayfanın glif metninde (get_texttrace) aranır; bulunmayanlar
  "metin katmanı farkı" sayılır, kurula gönderilmez, pay ve paydadan çıkarılıp ayrı raporlanır (testseti/araclar/k42_katman.py).
A: 30 kilitli sayfa (S01-S30; Biyoloji 9, Biyoloji 11, TDE 10). Talimatlar K39'unkinin aynısı.
"""
(PROJE / "testseti" / "bagimsiz2_kilit.txt").write_text(kilit, encoding="utf-8")
print("Kilit dosyası yazıldı: testseti/bagimsiz2_kilit.txt")
