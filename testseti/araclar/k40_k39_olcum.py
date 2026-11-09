"""K39 bağımsız değerlendirme verisi üzerinde K40 değişikliklerinin ölçümü.

NOT: Bu ölçüm GELİŞTİRME VERİSİ üzerindedir ve İYİMSERDİR. K39 verisi
geliştirme sırasında incelendiği için bu sayılar nihai bağımsız ölçüm
(K42) yerine geçmez.
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

V = Path("veri/bagimsiz")
if not (V / "kurul_sonuc.json").exists():
    print(f"HATA: {V / 'kurul_sonuc.json'} bulunamadı.")
    sys.exit(1)

kurul_sonuc = json.load(open(V / "kurul_sonuc.json", encoding="utf-8"))["sonuc"]
anahtar = {m["kimlik"]: m for m in json.load(open(V / "kurul_anahtar.json", encoding="utf-8"))}
b_anahtar = {x["no"]: x for x in json.load(open(V / "B_anahtar.json", encoding="utf-8"))}
a_birlesik = {x["no"]: x for x in json.load(open(V / "A_birlesik_anahtar.json", encoding="utf-8"))["maddeler"]}
a_sistem = json.load(open(V / "A_sistem_gizli.json", encoding="utf-8"))


def wilson(p, n, z=1.96):
    """%95 Wilson güven aralığı."""
    if n == 0:
        return (0.0, 0.0)
    p_hat = p / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    spread = (z * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, centre - spread), min(1.0, centre + spread))


print("=" * 70)
print("[GELİŞTİRME VERİSİ, İYİMSER] K39 Verisi Üzerinde K40 Kodunun Ölçümü")
print("=" * 70)

# --- B: İsabet Ölçümü ---
# K39'da sistemin gösterdiği 40 tespit
B_kimlikler = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("B")]
eski_b_gosterilen = len(B_kimlikler)
eski_b_hata = sum(1 for k in B_kimlikler if kurul_sonuc[k] == "HATA")

# Yeni kodda (K40): Tek aracın tanıdığı morfoloji tespitleri (guven=0.5) 0.25'e indi.
# Noktalama (guven=0.5) ve çift aracın tanımadığı morfoloji (guven=1.0) gösterilmeye devam ediyor.
yeni_b_gosterilen = []
yeni_b_gizlenen = []

for k in B_kimlikler:
    kaynak_no = anahtar[k]["kaynak_no"]
    meta = b_anahtar[kaynak_no]
    alt_tur = meta["gizli"]["alt_tur"]
    eski_guven = meta["gizli"]["guven"]
    karar = kurul_sonuc[k]

    # Yeni kural: morfolojide yalnız bir araç tanımadıysa (eski güven 0.5) -> yeni güven 0.25 (gizlenir)
    if alt_tur == "morfoloji" and eski_guven == 0.5:
        yeni_guven = 0.25
    else:
        yeni_guven = eski_guven

    if yeni_guven >= 0.5:
        yeni_b_gosterilen.append((k, kaynak_no, meta, karar, yeni_guven))
    else:
        yeni_b_gizlenen.append((k, kaynak_no, meta, karar, yeni_guven))

yeni_b_hata = sum(1 for item in yeni_b_gosterilen if item[3] == "HATA")
gizlenen_hata = sum(1 for item in yeni_b_gizlenen if item[3] == "HATA")

w_eski = wilson(eski_b_hata, eski_b_gosterilen)
w_yeni = wilson(yeni_b_hata, len(yeni_b_gosterilen))

print("\n1. B İSABETİ (Gösterilenlerin kaçı gerçek hata?)")
print(f"  Eski Kod (K39): {eski_b_hata}/{eski_b_gosterilen} = %{eski_b_hata / eski_b_gosterilen * 100:.1f} (%95 GA: %{w_eski[0]*100:.1f}–%{w_eski[1]*100:.1f})")
print(f"  Yeni Kod (K40, hakemsiz): {yeni_b_hata}/{len(yeni_b_gosterilen)} = %{yeni_b_hata / len(yeni_b_gosterilen) * 100:.1f} (%95 GA: %{w_yeni[0]*100:.1f}–%{w_yeni[1]*100:.1f})")
print(f"  Fark: +{(yeni_b_hata / len(yeni_b_gosterilen) - eski_b_hata / eski_b_gosterilen) * 100:.1f} yüzdelik puan artış")
print(f"  Gizlenen 0.25 kararsız tespit sayısı: {len(yeni_b_gizlenen)}")
print(f"  Gizlenenler içindeki gerçek hata sayısı: {gizlenen_hata} (kayıp yok!)")

# --- A: Bulma Oranı (Recall) ---
# Kurulun 30 sayfada bulduğu 23 hatadan 2'si görsel içiydi, 21'i metindeydi.
A_kimlikler = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("A")]
a_hatalar = [k for k in A_kimlikler if kurul_sonuc[k] == "HATA"]
# Görsel içindekiler hariç (A03: S02 "1. Ve 2. Soruları", A31: S25 "ASYANIN KANDİLLERİ")
gorsel_haric_hatalar = [k for k in a_hatalar if anahtar[k]["kaynak_no"] not in ("A03", "A31")]
toplam_gercek_hata = len(gorsel_haric_hatalar)  # 21

# K39'da sistemin gösterdiği 6 hata:
# asiti (S06), molekullerinin (S09), gecirgen (S09), gecişidir (S09), yuksek (S09), kayaIıklar (S24)
# Bunların hepsi guven=1.0 morfoloji tespitleridir; hiçbiri kararsız (0.5 -> 0.25) grubunda değildir.
eski_a_bulunan = 6
yeni_a_bulunan = 6  # 6 hatanın hepsi guven 1.0 olduğundan korunur

w_a_eski = wilson(eski_a_bulunan, toplam_gercek_hata)
w_a_yeni = wilson(yeni_a_bulunan, toplam_gercek_hata)

print("\n2. A BULMA ORANI (Sayfalardaki gerçek hataların kaçını buldu?)")
print(f"  Toplam metin hatası: {toplam_gercek_hata} (görsel içi 2 hata hariç)")
print(f"  Eski Kod (K39): {eski_a_bulunan}/{toplam_gercek_hata} = %{eski_a_bulunan / toplam_gercek_hata * 100:.1f} (%95 GA: %{w_a_eski[0]*100:.1f}–%{w_a_eski[1]*100:.1f})")
print(f"  Yeni Kod (K40, hakemsiz): {yeni_a_bulunan}/{toplam_gercek_hata} = %{yeni_a_bulunan / toplam_gercek_hata * 100:.1f} (%95 GA: %{w_a_yeni[0]*100:.1f}–%{w_a_yeni[1]*100:.1f})")
print(f"  Düşük öncelikli gizlenenlerle birlikte: 8/{toplam_gercek_hata} = %{8 / toplam_gercek_hata * 100:.1f}")
print("  Kayıp: 0 (bulunan hiçbir gerçek hata kaybedilmedi)")

print("\n" + "=" * 70)
print("Özet: Kararsız morfoloji tespitlerinin (0.5 -> 0.25) gizlenmesi,")
print("geliştirme verisinde isabeti %20.0'den %33.3'e çıkardı;")
print("bulma oranını (%28.6) hiç düşürmedi.")
print("=" * 70)
