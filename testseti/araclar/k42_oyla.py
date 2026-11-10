"""Kurul oylaması (ChatGPT, Gemini, DeepSeek) → çoğunluk etiketi; A ve B sonuçları; kilitli sistem çıktısıyla karşılaştırma."""
import json
import math
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

H, V = Path("bagimsiz_degerlendirme2"), Path("veri/bagimsiz2")
anahtar = {m["kimlik"]: m for m in json.load(open(V / "kurul_anahtar.json", encoding="utf-8"))}
b_anahtar = {x["no"]: x for x in json.load(open(V / "B_anahtar.json", encoding="utf-8"))}
a_birlesik = {x["no"]: x for x in json.load(open(V / "A_birlesik_anahtar.json", encoding="utf-8"))["maddeler"]}
sistem_a = json.load(open(V / "A_sistem_gizli.json", encoding="utf-8"))

files = {
    "chatgpt": "Kurul_GPT.txt",
    "gemini": "Kurul_Gemini.txt",
    "deepseek": "Kurul_DeekSeek.txt",
}


def oku(ad):
    oy = {}
    fname = files[ad]
    for satir in (H / fname).read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in re.split(r"\t|\|", satir)]
        if p and re.fullmatch(r"K\d{3}", p[0]):
            k = p[1].upper()
            oy[p[0]] = "HATA" if k == "HATA" else "EMIN" if k.startswith("EM") else "DEGIL"
            oy[p[0] + "_alt"] = p[1]
    return oy


KURUL = ["chatgpt", "gemini", "deepseek"]
oylar = {a: oku(a) for a in KURUL}
for a in KURUL:
    assert sum(k.startswith("K") and not k.endswith("_alt") for k in oylar[a]) == 120, a


def cogunluk(k):
    c = Counter(oylar[a][k] for a in KURUL)
    if c["HATA"] >= 2:
        return "HATA"
    if c["DEGIL"] >= 2:
        return "DEGIL"
    return "BELIRSIZ"


sonuc = {k: cogunluk(k) for k in anahtar}


def wilson(k, n, z=1.95996):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    diff = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return (max(0.0, center - diff), min(1.0, center + diff))


# Uyum: ikili ham uyum + Fleiss kappa (3 kategori)
def fleiss(kimlikler):
    kat = ["HATA", "DEGIL", "EMIN"]
    N, n = len(kimlikler), 3
    p = Counter()
    P = 0
    for k in kimlikler:
        c = Counter(oylar[a][k] for a in KURUL)
        P += (sum(v * v for v in c.values()) - n) / (n * (n - 1))
        p.update(c)
    P /= N
    Pe = sum((p[x] / (N * n)) ** 2 for x in kat)
    return (P - Pe) / (1 - Pe)


hepsi = list(anahtar)
ikili = {f"{a}-{b}": sum(oylar[a][k] == oylar[b][k] for k in hepsi) / len(hepsi) for a, b in combinations(KURUL, 2)}
ucu_ayni = sum(len({oylar[a][k] for a in KURUL}) == 1 for k in hepsi)

# --- B: sistemin tespitleri → isabet
B = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("B")]
b_hakemli = [k for k in B if b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["hakemli_gosterilen"]]
b_hakemsiz = [k for k in B if b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["hakemsiz_gosterilen"]]

b_hakemli_hata = [k for k in b_hakemli if sonuc[k] == "HATA"]
b_hakemsiz_hata = [k for k in b_hakemsiz if sonuc[k] == "HATA"]

b_kitap = Counter((anahtar[k]["kitap"], sonuc[k]) for k in b_hakemli)
b_tur = Counter((b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["alt_tur"], sonuc[k]) for k in b_hakemli)
b_guven = Counter((b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["guven_hakemli"], sonuc[k]) for k in b_hakemli)

# --- A: kurulun "HATA" dediği gerçek hatalar → sistem kaçını buldu
A = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("A")]
a_hatalar = [k for k in A if sonuc[k] == "HATA"]

tum_tespitler_h = {}
tum_tespitler_hs = {}
for s_inf in sistem_a:
    tum_tespitler_h[s_inf["sayfa"]] = [t for t in s_inf["hakemli"] if t["guven_skoru"] >= 0.5]
    tum_tespitler_hs[s_inf["sayfa"]] = [t for t in s_inf["hakemsiz"] if t["guven_skoru"] >= 0.5]


def a_eslestir(tum_tespitler):
    bulunan, kacirilan = [], []
    for k in a_hatalar:
        m = anahtar[k]
        b = a_birlesik[m["kaynak_no"]]
        gosterilen = tum_tespitler.get(b["sayfa"], [])
        eslesen = [t for t in gosterilen if t["metin_parcasi"] in b["kitaptaki"] or b["kitaptaki"] in t["metin_parcasi"]]
        if eslesen:
            bulunan.append((k, b, eslesen))
        else:
            kacirilan.append((k, b))
    return bulunan, kacirilan


a_bul_h, a_kac_h = a_eslestir(tum_tespitler_h)
a_bul_hs, a_kac_hs = a_eslestir(tum_tespitler_hs)

print("=== A: kurul kararları (HATA olanlar) ===")
for k in sorted(a_hatalar, key=lambda k: anahtar[k]["kaynak_no"]):
    m = anahtar[k]
    b = a_birlesik[m["kaynak_no"]]
    print(f"  {m['kaynak_no']} {k} {b['sayfa']} s.{b['sayfa_no']} | {sonuc[k]:8} | {'/'.join(oylar[a][k + '_alt'] for a in KURUL)} | «{b['kitaptaki'][:50]}» -> «{b['onerilen'][:30]}»")

print("\n=== B: kurul kararları (Hakemli Çıktı) ===")
for k in sorted(b_hakemli, key=lambda k: anahtar[k]["kaynak_no"]):
    m = anahtar[k]
    g = b_anahtar[m["kaynak_no"]]["gizli"]
    print(f"  {m['kaynak_no']} {k} {m['kitap']} s.{m['sayfa_no']} | {sonuc[k]:8} | {'/'.join(oylar[a][k + '_alt'] for a in KURUL)} | {g['alt_tur']} g={g['guven_hakemli']} | «{m['yazim']}»")

print("\n=== Özet ===")
w_h = wilson(len(b_hakemli_hata), len(b_hakemli))
w_hs = wilson(len(b_hakemsiz_hata), len(b_hakemsiz))
w_ah = wilson(len(a_bul_h), len(a_hatalar))
w_ahs = wilson(len(a_bul_hs), len(a_hatalar))

print(f"B İsabeti (Hakemli - Ana Sonuç): {len(b_hakemli_hata)}/{len(b_hakemli)} = %{100*len(b_hakemli_hata)/len(b_hakemli):.1f} (Wilson %95: %{100*w_h[0]:.1f} - %{100*w_h[1]:.1f})")
print(f"B İsabeti (Hakemsiz - İkincil):  {len(b_hakemsiz_hata)}/{len(b_hakemsiz)} = %{100*len(b_hakemsiz_hata)/len(b_hakemsiz):.1f} (Wilson %95: %{100*w_hs[0]:.1f} - %{100*w_hs[1]:.1f})")
print("  Hakemli kitaba göre:", dict(b_kitap))
print("  Hakemli türe göre:", dict(b_tur))
print("  Hakemli güvene göre:", dict(b_guven))
print(f"A Gerçek Hata Sayısı: {len(a_hatalar)} / {len(A)} aday")
print(f"A Bulma Oranı (Hakemli): {len(a_bul_h)}/{len(a_hatalar)} = %{100*len(a_bul_h)/len(a_hatalar):.1f} (Wilson %95: %{100*w_ah[0]:.1f} - %{100*w_ah[1]:.1f})")
print(f"A Bulma Oranı (Hakemsiz): {len(a_bul_hs)}/{len(a_hatalar)} = %{100*len(a_bul_hs)/len(a_hatalar):.1f} (Wilson %95: %{100*w_ahs[0]:.1f} - %{100*w_ahs[1]:.1f})")
print(f"Uyum: ikili { {k: round(v, 3) for k, v in ikili.items()} } | üçü aynı: {ucu_ayni} / 120 | Fleiss kappa: {fleiss(hepsi):.3f}")

json.dump(
    {
        "sonuc": sonuc,
        "oylar": {a: {k: v for k, v in oylar[a].items() if not k.endswith("_alt")} for a in KURUL},
        "b_hakemli": {
            "toplam": len(b_hakemli),
            "hata": len(b_hakemli_hata),
            "oran": len(b_hakemli_hata) / len(b_hakemli),
            "wilson_95": [w_h[0], w_h[1]],
        },
        "b_hakemsiz": {
            "toplam": len(b_hakemsiz),
            "hata": len(b_hakemsiz_hata),
            "oran": len(b_hakemsiz_hata) / len(b_hakemsiz),
            "wilson_95": [w_hs[0], w_hs[1]],
        },
        "a_gercek_hata": len(a_hatalar),
        "a_bulma_hakemli": {
            "bulunan": len(a_bul_h),
            "toplam": len(a_hatalar),
            "oran": len(a_bul_h) / len(a_hatalar),
            "wilson_95": [w_ah[0], w_ah[1]],
        },
        "a_bulma_hakemsiz": {
            "bulunan": len(a_bul_hs),
            "toplam": len(a_hatalar),
            "oran": len(a_bul_hs) / len(a_hatalar),
            "wilson_95": [w_ahs[0], w_ahs[1]],
        },
        "fleiss_kappa": fleiss(hepsi),
    },
    open(V / "kurul_sonuc.json", "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=1,
)
