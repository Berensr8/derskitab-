"""K45 Aşama 2.2: Kurul oylaması (ChatGPT, Gemini, DeepSeek) → çoğunluk etiketi; A ve B sonuçları;
kilitli sistem çıktısıyla karşılaştırma."""
import json
import math
import re
import sys
from collections import Counter
from itertools import combinations

from k45_ortak import CIKTI, K44_KURALLAR, KITAPLAR, PAKET, YENI_KURALLAR

sys.stdout.reconfigure(encoding="utf-8")

H, V = PAKET, CIKTI
anahtar = {m["kimlik"]: m for m in json.load(open(V / "kurul_anahtar.json", encoding="utf-8"))}
b_anahtar = {x["no"]: x for x in json.load(open(V / "B_anahtar.json", encoding="utf-8"))}
a_birlesik = {x["no"]: x for x in json.load(open(V / "A_birlesik_anahtar.json", encoding="utf-8"))["maddeler"]}
sistem_a = json.load(open(V / "A_sistem_gizli.json", encoding="utf-8"))

files = {
    "chatgpt": "KURUL_GPT.txt",
    "gemini": "KURUL_GEMİNİ.txt",
    "deepseek": "KURUL_DP.txt",
}


def _etiket(k: str) -> str:
    u = k.strip().upper()
    if u == "HATA":
        return "HATA"
    if u.startswith("EM"):
        return "EMIN"
    return "DEGIL"


def oku(ad: str) -> dict:
    oy = {}
    metin = (H / files[ad]).read_text(encoding="utf-8")
    if ad == "gemini" and "\n" not in metin.strip():
        # Tek satır bitişik tablo: K001...K002...
        parcalar = re.split(r"(?=K\d{3})", metin)
        for p in parcalar:
            m = re.match(
                r"^(K\d{3})\s*(HATA DEĞİL\s*\(alıntı\)|HATA DEĞİL\s*\(PDF\)|HATA DEĞİL|EMİN DEĞİLİM|HATA)(?=\s*(?:EVET|HAYIR|BİLİNMİYOR))",
                p.strip(),
                re.IGNORECASE,
            )
            if m:
                kimlik, karar = m.group(1), m.group(2).strip()
                oy[kimlik] = _etiket(karar)
                oy[kimlik + "_alt"] = karar
        return oy

    for satir in metin.splitlines():
        temiz = satir.strip().lstrip("\\|").strip()
        p = [x.strip() for x in re.split(r"\t|\|", temiz) if x.strip()]
        if p and re.fullmatch(r"K\d{3}", p[0]):
            karar = p[1]
            oy[p[0]] = _etiket(karar)
            oy[p[0] + "_alt"] = karar
    return oy


KURUL = ["chatgpt", "gemini", "deepseek"]
oylar = {a: oku(a) for a in KURUL}
for a in KURUL:
    say = sum(k.startswith("K") and not k.endswith("_alt") for k in oylar[a])
    assert say == len(anahtar), f"{a}: {say} != {len(anahtar)}"


def cogunluk(k: str) -> str:
    c = Counter(oylar[a][k] for a in KURUL)
    if c["HATA"] >= 2:
        return "HATA"
    if c["DEGIL"] >= 2:
        return "DEGIL"
    return "BELIRSIZ"


sonuc = {k: cogunluk(k) for k in anahtar}


def wilson(k: int, n: int, z: float = 1.95996) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    diff = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return (max(0.0, center - diff), min(1.0, center + diff))


def fleiss(kimlikler: list[str]) -> float:
    kat = ["HATA", "DEGIL", "EMIN"]
    N, n = len(kimlikler), 3
    p = Counter()
    P = 0.0
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

# --- B: sistemin tespitleri → isabet (katman farkı olan 4 aday kurula gitmedi, pay ve paydadan çıkarıldı)
B = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("B")]
b_hakemli = [k for k in B if b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["hakemli_gosterilen"]]
b_hakemsiz = [k for k in B if b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["hakemsiz_gosterilen"]]

b_hakemli_hata = [k for k in b_hakemli if sonuc[k] == "HATA"]
b_hakemsiz_hata = [k for k in b_hakemsiz if sonuc[k] == "HATA"]
b_hakemli_3 = [k for k in b_hakemli if sum(oylar[a][k] == "HATA" for a in KURUL) == 3]
b_hakemli_enaz1 = [k for k in b_hakemli if sum(oylar[a][k] == "HATA" for a in KURUL) >= 1]

b_kitap_h = Counter((anahtar[k]["kitap"], sonuc[k]) for k in b_hakemli)
b_kitap_hs = Counter((anahtar[k]["kitap"], sonuc[k]) for k in b_hakemsiz)
b_tur_h = Counter((b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["alt_tur"], sonuc[k]) for k in b_hakemli)
b_tur_tum = Counter((b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["alt_tur"], sonuc[k]) for k in B)
b_guven_h = Counter((b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["guven_hakemli"], sonuc[k]) for k in b_hakemli)
b_guven_hs = Counter((b_anahtar[anahtar[k]["kaynak_no"]]["gizli"]["guven_hakemsiz"], sonuc[k]) for k in b_hakemsiz)

# Yeni kurallar (K44 + buyuk_harf_i): B içinde "yeni:<alt>" kaynağı olanların tümü
yeni_kural_sonuc = {}
for alt in YENI_KURALLAR:
    k_list = [k for k in B if f"yeni:{alt}" in b_anahtar[anahtar[k]["kaynak_no"]]["kaynak"]]
    h_say = sum(sonuc[k] == "HATA" for k in k_list)
    katman_say = sum(
        1 for x in b_anahtar.values() if f"yeni:{alt}" in x["kaynak"] and bool(x.get("katman_farki"))
    )
    yeni_kural_sonuc[alt] = {"kurulda": len(k_list), "hata": h_say, "katman_farki": katman_say}

# --- A: kurulun "HATA" dediği gerçek hatalar → sistem kaçını buldu
A = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("A")]
a_hatalar = [k for k in A if sonuc[k] == "HATA"]

tum_tespitler_h = {}
tum_tespitler_hs = {}
tum_tespitler_gizli = {}
for s_inf in sistem_a:
    tum_tespitler_h[s_inf["sayfa"]] = [t for t in s_inf["hakemli"] if t["guven_skoru"] >= 0.5]
    tum_tespitler_hs[s_inf["sayfa"]] = [t for t in s_inf["hakemsiz"] if t["guven_skoru"] >= 0.5]
    tum_tespitler_gizli[s_inf["sayfa"]] = list(s_inf["hakemli"])


def _parca_eslesir(t_parca: str, a_kitaptaki: str) -> bool:
    if not t_parca:
        return False
    tp = t_parca.strip()
    ak = a_kitaptaki.strip()
    if tp in ak or ak in tp:
        return True
    # Kesme / boşluk / noktalama farklarıyla aynı ifadeyi yakalayan durumlar için kelime kesişimi
    kelimeler_t = [w for w in re.findall(r"\w+", tp.lower()) if len(w) >= 3]
    kelimeler_a = [w for w in re.findall(r"\w+", ak.lower()) if len(w) >= 3]
    if kelimeler_t and all(w in kelimeler_a for w in kelimeler_t):
        return True
    return False


def a_eslestir(tum_tespitler: dict):
    bulunan, kacirilan = [], []
    for k in a_hatalar:
        m = anahtar[k]
        b = a_birlesik[m["kaynak_no"]]
        gosterilen = tum_tespitler.get(b["sayfa"], [])
        eslesen = [t for t in gosterilen if _parca_eslesir(t["metin_parcasi"], b["kitaptaki"])]
        if eslesen:
            bulunan.append((k, b, eslesen))
        else:
            kacirilan.append((k, b))
    return bulunan, kacirilan


a_bul_h, a_kac_h = a_eslestir(tum_tespitler_h)
a_bul_hs, a_kac_hs = a_eslestir(tum_tespitler_hs)
a_bul_gizli, _ = a_eslestir(tum_tespitler_gizli)

print("=== A: kurul kararları (HATA olanlar) ===")
for k in sorted(a_hatalar, key=lambda k: anahtar[k]["kaynak_no"]):
    m = anahtar[k]
    b = a_birlesik[m["kaynak_no"]]
    es_h = [t["alt_tur"] for _, bb, es in a_bul_h if bb["no"] == b["no"] for t in es]
    es_g = [(t["alt_tur"], t["guven_skoru"]) for _, bb, es in a_bul_gizli if bb["no"] == b["no"] for t in es]
    print(
        f"  {m['kaynak_no']} {k} {b['sayfa']} ({b['kitap']} s.{b['sayfa_no']}) | {sonuc[k]:8} | "
        f"{'/'.join(oylar[a][k + '_alt'] for a in KURUL)} | «{b['kitaptaki'][:45]}» -> «{b['onerilen'][:30]}» | "
        f"gosterilen={es_h} tum={es_g}"
    )

print("\n=== B: kurul kararları (Hakemli Çıktı) ===")
for k in sorted(b_hakemli, key=lambda k: anahtar[k]["kaynak_no"]):
    m = anahtar[k]
    g = b_anahtar[m["kaynak_no"]]["gizli"]
    print(
        f"  {m['kaynak_no']} {k} {m['kitap']} s.{m['sayfa_no']} | {sonuc[k]:8} | "
        f"{'/'.join(oylar[a][k + '_alt'] for a in KURUL)} | {g['alt_tur']} g={g['guven_hakemli']} | «{m['yazim']}»"
    )

print("\n=== B: 80 örneklemi dışından eklenen yeni kural tespitleri ===")
for k in sorted([k for k in B if k not in b_hakemli], key=lambda k: anahtar[k]["kaynak_no"]):
    m = anahtar[k]
    x = b_anahtar[m["kaynak_no"]]
    g = x["gizli"]
    if any(ky.startswith("yeni:") for ky in x["kaynak"]):
        print(
            f"  {m['kaynak_no']} {k} {m['kitap']} s.{m['sayfa_no']} | {sonuc[k]:8} | "
            f"{'/'.join(oylar[a][k + '_alt'] for a in KURUL)} | {g['alt_tur']} kaynak={x['kaynak']} | «{m['yazim']}»"
        )

print("\n=== Özet ===")
w_h = wilson(len(b_hakemli_hata), len(b_hakemli))
w_hs = wilson(len(b_hakemsiz_hata), len(b_hakemsiz))
w_ah = wilson(len(a_bul_h), len(a_hatalar))
w_ahs = wilson(len(a_bul_hs), len(a_hatalar))
w_ag = wilson(len(a_bul_gizli), len(a_hatalar))

print(f"B İsabeti (Hakemli - Ana Sonuç): {len(b_hakemli_hata)}/{len(b_hakemli)} = %{100*len(b_hakemli_hata)/len(b_hakemli):.1f} (Wilson %95: %{100*w_h[0]:.1f} - %{100*w_h[1]:.1f})")
print(f"B İsabeti (Oybirliği 3/3):       {len(b_hakemli_3)}/{len(b_hakemli)} = %{100*len(b_hakemli_3)/len(b_hakemli):.1f}")
print(f"B İsabeti (En az 1 HATA):        {len(b_hakemli_enaz1)}/{len(b_hakemli)} = %{100*len(b_hakemli_enaz1)/len(b_hakemli):.1f}")
print(f"B İsabeti (Hakemsiz - İkincil):  {len(b_hakemsiz_hata)}/{len(b_hakemsiz)} = %{100*len(b_hakemsiz_hata)/len(b_hakemsiz):.1f} (Wilson %95: %{100*w_hs[0]:.1f} - %{100*w_hs[1]:.1f})")
print("  Hakemli kitaba göre:", dict(b_kitap_h))
print("  Hakemsiz kitaba göre:", dict(b_kitap_hs))
print("  Hakemli türe göre:", dict(b_tur_h))
print("  Birleşik B türe göre:", dict(b_tur_tum))
print("  Hakemli güvene göre:", dict(b_guven_h))
print("  Hakemsiz güvene göre:", dict(b_guven_hs))
print("  Yeni kurallar (K44 + buyuk_harf_i):", yeni_kural_sonuc)
print(f"A Gerçek Hata Sayısı: {len(a_hatalar)} / {len(A)} aday")
print(f"A Bulma Oranı (Hakemli gösterilen): {len(a_bul_h)}/{len(a_hatalar)} = %{100*len(a_bul_h)/len(a_hatalar):.1f} (Wilson %95: %{100*w_ah[0]:.1f} - %{100*w_ah[1]:.1f})")
print(f"A Bulma Oranı (Hakemsiz gösterilen): {len(a_bul_hs)}/{len(a_hatalar)} = %{100*len(a_bul_hs)/len(a_hatalar):.1f} (Wilson %95: %{100*w_ahs[0]:.1f} - %{100*w_ahs[1]:.1f})")
print(f"A Bulma Oranı (Gizliler dahil):      {len(a_bul_gizli)}/{len(a_hatalar)} = %{100*len(a_bul_gizli)/len(a_hatalar):.1f} (Wilson %95: %{100*w_ag[0]:.1f} - %{100*w_ag[1]:.1f})")
print(f"Uyum: ikili { {k: round(v, 3) for k, v in ikili.items()} } | üçü aynı: {ucu_ayni} / {len(hepsi)} | Fleiss kappa: {fleiss(hepsi):.3f}")

json.dump(
    {
        "sonuc": sonuc,
        "oylar": {a: {k: v for k, v in oylar[a].items() if not k.endswith("_alt")} for a in KURUL},
        "b_hakemli": {
            "toplam": len(b_hakemli),
            "hata": len(b_hakemli_hata),
            "oran": len(b_hakemli_hata) / len(b_hakemli),
            "wilson_95": [w_h[0], w_h[1]],
            "katman_farki_haric": 4,
        },
        "b_hakemsiz": {
            "toplam": len(b_hakemsiz),
            "hata": len(b_hakemsiz_hata),
            "oran": len(b_hakemsiz_hata) / len(b_hakemsiz),
            "wilson_95": [w_hs[0], w_hs[1]],
            "katman_farki_haric": 0,
        },
        "yeni_kurallar": yeni_kural_sonuc,
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
        "a_bulma_gizli_dahil": {
            "bulunan": len(a_bul_gizli),
            "toplam": len(a_hatalar),
            "oran": len(a_bul_gizli) / len(a_hatalar),
            "wilson_95": [w_ag[0], w_ag[1]],
        },
        "fleiss_kappa": fleiss(hepsi),
    },
    open(V / "kurul_sonuc.json", "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=1,
)
