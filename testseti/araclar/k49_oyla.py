"""K49 Aşama 2.3: kurul oyları (ChatGPT, Gemini, DeepSeek) → çoğunluk etiketi; ön kayıttaki ölçüler
(testseti/k49_on_kayit.md §4-5). Okuma ve eşleşme kuralları k45_oyla.py ile aynıdır."""
import json
import math
import re
import sys
from collections import Counter
from itertools import combinations

from k49_ortak import CIKTI, KURALLAR, PAKET

sys.stdout.reconfigure(encoding="utf-8")
V = CIKTI
anahtar = {m["kimlik"]: m for m in json.load(open(V / "kurul_anahtar.json", encoding="utf-8"))}
b_anahtar = {x["no"]: x for x in json.load(open(V / "B_anahtar.json", encoding="utf-8"))}
a_birlesik = {x["no"]: x for x in json.load(open(V / "A_birlesik_anahtar.json", encoding="utf-8"))["maddeler"]}
sistem_a = json.load(open(V / "A_sistem_gizli.json", encoding="utf-8"))
nufus = json.load(open(V / "B_nufus.json", encoding="utf-8"))
B_SAYFA = 478

DOSYA = {"chatgpt": "KURUL_GPT.txt", "gemini": "KURUL_GEMİNİ.txt", "deepseek": "KURUL_DEEPSEEK.txt"}
KURUL = list(DOSYA)
KARAR = r"(HATA DEĞİL\s*\(alıntı\)|HATA DEĞİL\s*\(PDF\)|HATA DEĞİL|EMİN DEĞİLİM|HATA)"


def etiket(k: str) -> str:
    u = k.strip().upper()
    return "HATA" if u == "HATA" else "EMIN" if u.startswith("EM") else "DEGIL"


def oku(ad: str) -> dict:
    metin = (PAKET / DOSYA[ad]).read_text(encoding="utf-8")
    oy = {}
    if "\n" not in metin.strip():  # sütun ayraçları kaybolmuş tek satır (Gemini)
        for m in re.finditer(r"(K\d{3})\s*" + KARAR + r"(?=\s*(?:EVET|HAYIR|BİLİNMİYOR))", metin, re.IGNORECASE):
            oy.setdefault(m.group(1), m.group(2).strip())
    else:
        for satir in metin.splitlines():
            p = [x.strip() for x in re.split(r"\t|\|", satir.strip()) if x.strip()]
            if p and re.fullmatch(r"K\d{3}", p[0]):
                oy.setdefault(p[0], p[1])
    return oy


ham = {a: oku(a) for a in KURUL}
for a in KURUL:
    assert set(ham[a]) == set(anahtar), f"{a}: {len(ham[a])} karar, eksik {sorted(set(anahtar) - set(ham[a]))[:5]}"
oylar = {a: {k: etiket(v) for k, v in ham[a].items()} for a in KURUL}


def cogunluk(k: str) -> str:
    c = Counter(oylar[a][k] for a in KURUL)
    return "HATA" if c["HATA"] >= 2 else "DEGIL" if c["DEGIL"] >= 2 else "BELIRSIZ"


sonuc = {k: cogunluk(k) for k in anahtar}


def wilson(k: int, n: int, z: float = 1.95996) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def fleiss(kim: list[str]) -> float:
    n, p, P = 3, Counter(), 0.0
    for k in kim:
        c = Counter(oylar[a][k] for a in KURUL)
        P += (sum(v * v for v in c.values()) - n) / (n * (n - 1))
        p.update(c)
    P /= len(kim)
    Pe = sum((p[x] / (len(kim) * n)) ** 2 for x in ("HATA", "DEGIL", "EMIN"))
    return (P - Pe) / (1 - Pe)


def oran(liste: list[str]) -> dict:
    h = sum(sonuc[k] == "HATA" for k in liste)
    return {"hata": h, "toplam": len(liste), "oran": h / len(liste) if liste else None, "wilson_95": wilson(h, len(liste))}


def yuzde(d: dict) -> str:
    if not d["toplam"]:
        return "0/0"
    return f"{d['hata']}/{d['toplam']} = %{100 * d['oran']:.1f} (%{100 * d['wilson_95'][0]:.1f}–%{100 * d['wilson_95'][1]:.1f})"


# ------------------------------------------------------------------ B
B = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("B")]
bx = {k: b_anahtar[anahtar[k]["kaynak_no"]] for k in B}
B1 = [k for k in B if "B1" in bx[k]["katman"]]
B2 = [k for k in B if "B2" in bx[k]["katman"]]
b1, b2 = oran(B1), oran(B2)
N1, N2 = nufus["N1"], nufus["N2"]
katmanli = (N1 * b1["oran"] + N2 * b2["oran"]) / (N1 + N2)
# Katman farkları (kurula gitmedi): B1 örneğinde 17. Editör ekranında bunlar yanlış alarmdır; duyarlılık için
# B1 isabeti katman farkları "hata değil" sayılarak da verilir (ön kayıttaki ana ölçü değil).
b1_katman_farki = sum(1 for x in b_anahtar.values() if "B1" in x["katman"] and x["katman_farki"])
b1_editor = b1["hata"] / (b1["toplam"] + b1_katman_farki)
katmanli_editor = (N1 * b1_editor + N2 * b2["oran"]) / (N1 + N2)

guven = {}
for g in (1.0, 0.75, 0.5):
    guven[str(g)] = oran([k for k in B1 if bx[k]["gizli"]["guven"] == g])

kural = {}
for alt in KURALLAR:
    b3 = [k for k in B if f"B3:{alt}" in bx[k]["katman"]]
    hepsi = [k for k in B if bx[k]["gizli"]["alt_tur"] == alt]
    kf = sum(1 for x in b_anahtar.values() if x["gizli"]["alt_tur"] == alt and x["katman_farki"])
    if b3 or hepsi or kf:
        kural[alt] = {"B3": oran(b3), "B1_B3": oran(hepsi), "katman_farki": kf}
tur_b1 = Counter((bx[k]["gizli"]["alt_tur"], sonuc[k]) for k in B1)
kitap_b = {kat: Counter((anahtar[k]["kitap"], sonuc[k]) for k in L) for kat, L in (("B1", B1), ("B2", B2))}

# ------------------------------------------------------------------ A
A = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("A")]
a_hata = [k for k in A if sonuc[k] == "HATA"]


def eslesir(t_parca: str, a_kitaptaki: str) -> bool:  # k45_oyla._parca_eslesir ile aynı
    if not t_parca:
        return False
    tp, ak = t_parca.strip(), a_kitaptaki.strip()
    if tp in ak or ak in tp:
        return True
    kt = [w for w in re.findall(r"\w+", tp.lower()) if len(w) >= 3]
    ka = [w for w in re.findall(r"\w+", ak.lower()) if len(w) >= 3]
    return bool(kt) and all(w in ka for w in kt)


def tespitler(kosul) -> dict:
    return {s["sayfa"]: [t for t in s["sistem"] if kosul(t)] for s in sistem_a}


ACIK = tespitler(lambda t: t["guven_skoru"] >= 0.5)
KAPALI = tespitler(lambda t: t["guven_skoru"] >= 0.5 and t["alt_tur"] != "sayfa_okuma")
GIZLI = tespitler(lambda t: True)


def bul(tum: dict) -> dict:
    sonucu = {}
    for k in a_hata:
        b = a_birlesik[anahtar[k]["kaynak_no"]]
        sonucu[k] = [(t["alt_tur"], t["guven_skoru"], t["metin_parcasi"]) for t in tum.get(b["sayfa"], [])
                     if eslesir(t["metin_parcasi"], b["kitaptaki"])]
    return sonucu


bul_acik, bul_kapali, bul_gizli = bul(ACIK), bul(KAPALI), bul(GIZLI)
n_acik = sum(bool(v) for v in bul_acik.values())
n_kapali = sum(bool(v) for v in bul_kapali.values())
n_gizli = sum(bool(v) for v in bul_gizli.values())
katki = n_acik - n_kapali
NA = len(a_hata)

# ------------------------------------------------------------------ ölçütler
def ol(v):
    return None if v is None else bool(v)


g1, g075 = guven["1.0"], guven["0.75"]
olcut = {
    "1_urun_isabeti_35": ol(katmanli >= 0.35),
    "2_bulma_30": ol(NA and n_acik / NA >= 0.30),
    "3_sayfa_okuma_katkisi": ol(katki >= 3 and katki >= 0.10 * NA),
    "4_sayfa_okuma_isabeti_30": ol(b2["oran"] >= 0.30),
    "5_oncelik_ters_degil": (None if g1["toplam"] < 5 or g075["toplam"] < 5 else g1["oran"] >= g075["oran"]),
    "6_kural_50": {alt: (None if v["B3"]["toplam"] < 3 else v["B3"]["oran"] >= 0.5) for alt, v in kural.items()},
}

# ------------------------------------------------------------------ yazdır
hepsi_k = list(anahtar)
print("=== A: kurulun HATA dediği gerçek hatalar ===")
for k in sorted(a_hata, key=lambda k: anahtar[k]["kaynak_no"]):
    b = a_birlesik[anahtar[k]["kaynak_no"]]
    print(f"  {b['no']} {k} {b['sayfa']} ({b['kitap']} s.{b['sayfa_no']}) {'/'.join(ham[a][k] for a in KURUL)} | "
          f"«{b['kitaptaki']}» → «{b['onerilen']}» | açık={bul_acik[k]} kapalı={bool(bul_kapali[k])} gizli={bul_gizli[k] if not bul_acik[k] else ''}")
print("\n=== A: HATA dışı ===")
for k in sorted(set(A) - set(a_hata), key=lambda k: anahtar[k]["kaynak_no"]):
    b = a_birlesik[anahtar[k]["kaynak_no"]]
    print(f"  {b['no']} {k} {b['sayfa']} {sonuc[k]:8} {'/'.join(ham[a][k] for a in KURUL)} | «{b['kitaptaki']}»")
for ad, L in (("B1", B1), ("B2", B2), ("B3", [k for k in B if k not in B1 and k not in B2])):
    print(f"\n=== {ad} ===")
    for k in sorted(L, key=lambda k: anahtar[k]["kaynak_no"]):
        x = bx[k]
        print(f"  {x['no']} {k} {x['kitap']} s.{x['sayfa_no']} | {sonuc[k]:8} | {'/'.join(ham[a][k] for a in KURUL)} | "
              f"{x['gizli']['alt_tur']} g={x['gizli']['guven']} | «{x['parca'][:70]}»")

print("\n=== Özet ===")
print(f"B1 (mevcut hat) isabet: {yuzde(b1)}; katman farkı (kurul dışı) {b1_katman_farki}")
print(f"B2 (sayfa okuma) isabet: {yuzde(b2)}")
print(f"Nüfus N1={N1}, N2={N2}; sayfa okuma gösterilen sayfa başına {N2 / B_SAYFA:.2f}")
print(f"Ürün isabeti (katmanlı, sayfa okuma dahil): %{100 * katmanli:.1f}; editör gözüyle (katman farkı yanlış alarm): %{100 * katmanli_editor:.1f}")
print("Güven (B1):", {g: yuzde(v) for g, v in guven.items()})
print("Kural:", {a: {"B3": yuzde(v["B3"]), "B1+B3": yuzde(v["B1_B3"]), "katman_farki": v["katman_farki"]} for a, v in kural.items()})
print("B1 türe göre:", dict(tur_b1))
print("Kitaba göre:", {k: dict(v) for k, v in kitap_b.items()})
print(f"A gerçek hata: {NA}/{len(A)} aday; belirsiz {sum(sonuc[k] == 'BELIRSIZ' for k in A)}")
print(f"Bulma: açık {n_acik}/{NA} = %{100 * n_acik / NA:.1f} {wilson(n_acik, NA)}; kapalı {n_kapali}/{NA}; "
      f"gizliler dahil {n_gizli}/{NA}; sayfa okuma katkısı {katki}")
ikili = {f"{a}-{b}": round(sum(oylar[a][k] == oylar[b][k] for k in hepsi_k) / len(hepsi_k), 3) for a, b in combinations(KURUL, 2)}
kappa = fleiss(hepsi_k)
print(f"Uyum: {ikili}; Fleiss κ = {kappa:.3f}")
print("ÖLÇÜTLER:", olcut)

json.dump({
    "sonuc": sonuc, "oylar_ham": ham, "B1": b1, "B2": b2, "N1": N1, "N2": N2,
    "sayfa_okuma_sayfa_basi": N2 / B_SAYFA, "urun_isabeti_katmanli": katmanli,
    "urun_isabeti_editor": katmanli_editor, "b1_katman_farki": b1_katman_farki, "guven_B1": guven, "kural": kural,
    "a_gercek_hata": NA, "a_aday": len(A), "bulma_acik": n_acik, "bulma_kapali": n_kapali, "bulma_gizli_dahil": n_gizli,
    "sayfa_okuma_katkisi": katki, "bulma_acik_wilson": wilson(n_acik, NA), "fleiss_kappa": kappa, "ikili_uyum": ikili,
    "olcutler": olcut,
}, open(V / "kurul_sonuc.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
