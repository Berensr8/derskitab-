"""Kurul oylaması (ChatGPT, Gemini, DeepSeek) → çoğunluk etiketi; A ve B sonuçları; kilitli sistem çıktısıyla karşılaştırma."""
import json, re, sys
from collections import Counter
from itertools import combinations
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

H, V = Path("bagimsiz_degerlendirme"), Path("veri/bagimsiz")
anahtar = {m["kimlik"]: m for m in json.load(open(V / "kurul_anahtar.json", encoding="utf-8"))}

def oku(ad):
    oy = {}
    for satir in open(H / f"KURUL_{ad}.txt", encoding="utf-8"):
        p = [x.strip() for x in re.split(r"\t|\|", satir)]
        if p and re.fullmatch(r"K\d{3}", p[0]):
            k = p[1].upper()
            oy[p[0]] = "HATA" if k == "HATA" else "EMIN" if k.startswith("EM") else "DEGIL"
            oy[p[0] + "_alt"] = p[1]
    return oy

KURUL = ["chatgpt", "gemini", "deepseek"]
oylar = {a: oku(a) for a in KURUL}
for a in KURUL:
    assert sum(k.startswith("K") and not k.endswith("_alt") for k in oylar[a]) == 102, a

def cogunluk(k):
    c = Counter(oylar[a][k] for a in KURUL)
    if c["HATA"] >= 2: return "HATA"
    if c["DEGIL"] >= 2: return "DEGIL"
    return "BELIRSIZ"

sonuc = {k: cogunluk(k) for k in anahtar}

# Uyum: ikili ham uyum + Fleiss kappa (3 kategori)
def fleiss(kimlikler):
    kat = ["HATA", "DEGIL", "EMIN"]
    N, n = len(kimlikler), 3
    p = Counter(); P = 0
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

# --- B: sistemin gösterdiği 40 tespit → isabet
B = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("B")]
bs = Counter(sonuc[k] for k in B)
b_anahtar = {x["no"]: x for x in json.load(open(V / "B_anahtar.json", encoding="utf-8"))}
b_kitap = Counter((anahtar[k]["kitap"], sonuc[k]) for k in B)
b_tur = Counter((b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["alt_tur"], sonuc[k]) for k in B)
b_guven = Counter((b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["guven"], sonuc[k]) for k in B)

# --- A: kurulun "HATA" dediği gerçek hatalar → sistem kaçını buldu (kilitli çıktı)
A = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("A")]
a_birlesik = {x["no"]: x for x in json.load(open(V / "A_birlesik_anahtar.json", encoding="utf-8"))["maddeler"]}
sistem = json.load(open(V / "A_sistem_gizli.json", encoding="utf-8"))
print("=== Kilitli sistem çıktısı (A sayfaları) ===")
for s in sistem:
    print(f"  {s['sayfa']} s.{s['sayfa_no']} | {s['alt_tur']} | güven {s['guven_skoru']} | «{s['metin_parcasi']}»")

print("\n=== A: kurul kararları ===")
for k in sorted(A, key=lambda k: anahtar[k]["kaynak_no"]):
    m = anahtar[k]; b = a_birlesik[m["kaynak_no"]]
    print(f"  {m['kaynak_no']} {k} {b['sayfa']} | {sonuc[k]:8} | {'/'.join(oylar[a][k + '_alt'] for a in KURUL)} | «{b['kitaptaki'][:60]}» | buldu:{','.join(b['kaynak'])}")

print("\n=== B: kurul kararları ===")
for k in sorted(B, key=lambda k: anahtar[k]["kaynak_no"]):
    m = anahtar[k]; g = b_anahtar[m["kaynak_no"]]["gizli"]
    print(f"  {m['kaynak_no']} {k} {m['kitap']} s.{m['sayfa_no']} | {sonuc[k]:8} | {'/'.join(oylar[a][k + '_alt'] for a in KURUL)} | {g['alt_tur']} {g['guven']} | «{m['yazim']}»")

print("\n=== Özet ===")
print("B (sistemin gösterdiği 40):", dict(bs))
print("  kitaba göre:", dict(b_kitap))
print("  türe göre:", dict(b_tur))
print("  güvene göre:", dict(b_guven))
print("A (62 aday):", dict(Counter(sonuc[k] for k in A)))
print("Uyum: ikili", {k: round(v, 3) for k, v in ikili.items()}, "| üçü aynı:", ucu_ayni, "/ 102 | Fleiss kappa:", round(fleiss(hepsi), 3))
json.dump({"sonuc": sonuc, "oylar": {a: {k: v for k, v in oylar[a].items() if not k.endswith('_alt')} for a in KURUL}},
          open(V / "kurul_sonuc.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
