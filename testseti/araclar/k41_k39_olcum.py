"""K39 bağımsız değerlendirme verisi üzerinde K41 kodunun gerçek çalıştırılması ve ölçümü.

Bu betik K39'un 30 A sayfasını ve 40 B tespitini 'yazim.analiz_et' + 'dusuk_oncelik.isaretle'
zincirini gerçek zamanlı olarak çalıştırarak mekanik biçimde eşleştirir.
Sonuçlar hem K39'un 21 metin hatası zemininde hem de K41-ek ile düzeltilen
17 gerçek basım hatası zemininde hesaplanır.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from derskitabi.kayit import bloklari_yukle
from derskitabi.kriterler import dusuk_oncelik, yazim

V = Path("testseti/bagimsiz")
if not (V / "kurul_sonuc.json").exists():
    V = Path("veri/bagimsiz")

if not (V / "kurul_sonuc.json").exists():
    print(f"HATA: {V / 'kurul_sonuc.json'} bulunamadı.")
    sys.exit(1)

kurul_sonuc = json.load(open(V / "kurul_sonuc.json", encoding="utf-8"))["sonuc"]
anahtar = {m["kimlik"]: m for m in json.load(open(V / "kurul_anahtar.json", encoding="utf-8"))}
b_anahtar = {x["no"]: x for x in json.load(open(V / "B_anahtar.json", encoding="utf-8"))}
a_birlesik = {x["no"]: x for x in json.load(open(V / "A_birlesik_anahtar.json", encoding="utf-8"))["maddeler"]}
a_sayfalar = json.load(open(V / "A_sayfa_listesi.json", encoding="utf-8"))


def wilson(p, n, z=1.96):
    """%95 Wilson güven aralığı."""
    if n == 0:
        return (0.0, 0.0)
    p_hat = p / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    spread = (z * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, centre - spread), min(1.0, centre + spread))


kitap_map = {
    "biyoloji9": "biyoloji9",
    "biyoloji11": "biyoloji11",
    "turkdili10": "turkdili10",
    "tde10": "turkdili10",
    "turkdili11": "turkdili11",
    "turkdili12": "turkdili12",
}

print("=" * 70)
print("[GELİŞTİRME VERİSİ, GERÇEK ÇALIŞTIRMA] K39 Verisi Üzerinde K41-ek Ölçümü")
print("=" * 70)

# =====================================================================
# 1. B İSABETİ (Gösterilenlerin kaçı gerçek hata?)
# =====================================================================
B_kimlikler = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("B")]
eski_b_gosterilen = len(B_kimlikler)  # 40
eski_b_hata = sum(1 for k in B_kimlikler if kurul_sonuc[k] == "HATA")  # 8

yeni_b_gosterilen = []
yeni_b_gizlenen = []

# Kitap bloklarını bir kez önbelleğe al
kitap_bloklari_onbellek = {}
for k_ad in ["biyoloji9", "biyoloji11", "turkdili10", "turkdili11", "turkdili12"]:
    blok_yol = Path(f"veri/{k_ad}_bloklar.json")
    if blok_yol.exists():
        kitap_bloklari_onbellek[k_ad] = bloklari_yukle(blok_yol)

for k in B_kimlikler:
    m = anahtar[k]
    meta = b_anahtar[m["kaynak_no"]]
    kitap = kitap_map.get(meta["kitap"], meta["kitap"])
    sayfa_no = meta["sayfa_no"]
    parca = meta["parca"]
    karar = kurul_sonuc[k]

    tum_bloklar = kitap_bloklari_onbellek.get(kitap, [])
    sayfa_bloklari = [b for b in tum_bloklar if b.sayfa_no == sayfa_no]
    pdf_yolu = Path(f"veri/{kitap}.pdf")

    tespitler = yazim.analiz_et(sayfa_bloklari, kitap_bloklari=tum_bloklar)
    if pdf_yolu.exists():
        tespitler = dusuk_oncelik.isaretle(pdf_yolu, sayfa_bloklari, tespitler)

    # Parça eşleşmesi ara
    eslesen = next((t for t in tespitler if t.metin_parcasi == parca or parca in (t.metin_parcasi or "")), None)

    if eslesen is not None and eslesen.guven_skoru >= 0.5:
        yeni_b_gosterilen.append((k, m["kaynak_no"], parca, karar, eslesen))
    else:
        yeni_b_gizlenen.append((k, m["kaynak_no"], parca, karar, eslesen))

yeni_b_hata = sum(1 for item in yeni_b_gosterilen if item[3] == "HATA")
gizlenen_hata = sum(1 for item in yeni_b_gizlenen if item[3] == "HATA")

w_b_eski = wilson(eski_b_hata, eski_b_gosterilen)
w_b_yeni = wilson(yeni_b_hata, len(yeni_b_gosterilen))

print("\n1. B İSABETİ (Gösterilenlerin kaçı gerçek hata?)")
print(f"  Eski Kod (K39): {eski_b_hata}/{eski_b_gosterilen} = %{eski_b_hata / eski_b_gosterilen * 100:.1f} (%95 GA: %{w_b_eski[0]*100:.1f}–%{w_b_eski[1]*100:.1f})")
print(f"  Yeni Kod (K41-ek, hakemsiz): {yeni_b_hata}/{len(yeni_b_gosterilen)} = %{yeni_b_hata / len(yeni_b_gosterilen) * 100:.1f} (%95 GA: %{w_b_yeni[0]*100:.1f}–%{w_b_yeni[1]*100:.1f})")
print(f"  Gizlenen / Düşen tespit sayısı: {len(yeni_b_gizlenen)}")
print(f"  Gizlenenler içindeki gerçek hata sayısı: {gizlenen_hata}")

# =====================================================================
# 2. A BULMA ORANI (Sayfalardaki gerçek hataların kaçını buldu?)
# =====================================================================
A_kimlikler = [k for k, m in anahtar.items() if m["kaynak_no"].startswith("A")]
a_hatalar = [k for k in A_kimlikler if kurul_sonuc[k] == "HATA"]
# Görsel içi 2 hata hariç: A03 ("1. Ve 2. Soruları"), A31 ("ASYANIN KANDİLLERİ")
gorsel_haric_hatalar = [k for k in a_hatalar if anahtar[k]["kaynak_no"] not in ("A03", "A31")]
toplam_metin_hatasi = len(gorsel_haric_hatalar)  # 21

# Sahte metin katmanı farkları (K41-ek): A01 (TAHRIŞ EDICI), A48 (DINLEME), A16 (Anahtarı’’), A25 (”Yüce)
SAHTE_KATMAN = {"A01", "A48", "A16", "A25"}
gercek_basim_hatalari = [k for k in gorsel_haric_hatalar if anahtar[k]["kaynak_no"] not in SAHTE_KATMAN]
toplam_gercek_basim_hatasi = len(gercek_basim_hatalari)  # 17

# 30 A sayfasını tek tek tara
bulunan_metin_hatalari = set()

for entry in a_sayfalar:
    k_kod = entry["kitap"]
    kitap_adi = kitap_map.get(k_kod, k_kod)
    sayfa_no = entry["sayfa_no"]

    tum_bloklar = kitap_bloklari_onbellek.get(kitap_adi, [])
    sayfa_bloklari = [b for b in tum_bloklar if b.sayfa_no == sayfa_no]
    if not sayfa_bloklari:
        continue

    tespitler = yazim.analiz_et(sayfa_bloklari, kitap_bloklari=tum_bloklar)
    pdf_yolu = Path(f"veri/{kitap_adi}.pdf")
    if pdf_yolu.exists():
        tespitler = dusuk_oncelik.isaretle(pdf_yolu, sayfa_bloklari, tespitler)

    gosterilen = [t for t in tespitler if t.guven_skoru >= 0.5]

    for k in gorsel_haric_hatalar:
        m = anahtar[k]
        a_madde = a_birlesik[m["kaynak_no"]]
        if a_madde["kitap"] == k_kod and a_madde["sayfa_no"] == sayfa_no:
            hata_metin = a_madde.get("parca", a_madde.get("hata_metni", a_madde.get("kelime", "")))
            # Eşleşme kontrolü
            for t in gosterilen:
                if (t.metin_parcasi in hata_metin or hata_metin in (t.metin_parcasi or "")
                        or any(w in (t.metin_parcasi or "") for w in hata_metin.split() if len(w) >= 3)):
                    bulunan_metin_hatalari.add(k)
                    break

bulunan_toplam_metin = len(bulunan_metin_hatalari)
bulunan_gercek_basim = len([k for k in bulunan_metin_hatalari if anahtar[k]["kaynak_no"] not in SAHTE_KATMAN])

w_a21_eski = wilson(6, toplam_metin_hatasi)
w_a21_yeni = wilson(bulunan_toplam_metin, toplam_metin_hatasi)
w_a17_eski = wilson(6, toplam_gercek_basim_hatasi)
w_a17_yeni = wilson(bulunan_gercek_basim, toplam_gercek_basim_hatasi)

print("\n2. A BULMA ORANI (Sayfalardaki gerçek hataların kaçını buldu?)")
print("  --- K39 Zemininde (21 metin adayı) ---")
print(f"  Eski Kod (K39): 6/{toplam_metin_hatasi} = %{6 / toplam_metin_hatasi * 100:.1f} (%95 GA: %{w_a21_eski[0]*100:.1f}–%{w_a21_eski[1]*100:.1f})")
print(f"  Yeni Kod (K41-ek, hakemsiz): {bulunan_toplam_metin}/{toplam_metin_hatasi} = %{bulunan_toplam_metin / toplam_metin_hatasi * 100:.1f} (%95 GA: %{w_a21_yeni[0]*100:.1f}–%{w_a21_yeni[1]*100:.1f})")

print("\n  --- K41-ek Düzeltilmiş Zemininde (17 gerçek basım hatası) ---")
print(f"  Eski Kod (K39): 6/{toplam_gercek_basim_hatasi} = %{6 / toplam_gercek_basim_hatasi * 100:.1f} (%95 GA: %{w_a17_eski[0]*100:.1f}–%{w_a17_eski[1]*100:.1f})")
print(f"  Yeni Kod (K41-ek, hakemsiz): {bulunan_gercek_basim}/{toplam_gercek_basim_hatasi} = %{bulunan_gercek_basim / toplam_gercek_basim_hatasi * 100:.1f} (%95 GA: %{w_a17_yeni[0]*100:.1f}–%{w_a17_yeni[1]*100:.1f})")

print("\n" + "=" * 70)
print(f"Özet (K41-ek): B isabeti %{yeni_b_hata/len(yeni_b_gosterilen)*100:.1f} ({yeni_b_hata}/{len(yeni_b_gosterilen)}), "
      f"A bulma oranı %{bulunan_gercek_basim/toplam_gercek_basim_hatasi*100:.1f} ({bulunan_gercek_basim}/{toplam_gercek_basim_hatasi} gerçek basım hatası).")
print("=" * 70)
