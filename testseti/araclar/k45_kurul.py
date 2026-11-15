"""K45 Aşama 2.1: Üç yapay zekâlı kurul için tek talimat: A (68 madde) + B (129 katman-temiz madde = 133 - 4 katman farkı),
karışık sırada, kaynağı belli olmayan nötr kimliklerle (K001…). Öneri/gerekçe gösterilmez; yalnız kitaptaki yazım ve bağlam."""
import json
import random
import re
import sys
from openpyxl import load_workbook

from k45_ortak import CIKTI, KITAP_AD, PAKET, PROJE, TOHUM, sha256_dosya_lf

sys.stdout.reconfigure(encoding="utf-8")

H = PAKET
V = CIKTI

ws = load_workbook(H / "A_benim_kararlarim.xlsx").active
a_baglam = {r[0].value: r[7].value for r in ws.iter_rows(min_row=2)}
a = json.load(open(V / "A_birlesik_anahtar.json", encoding="utf-8"))["maddeler"]


def notr(metin: str) -> str:
    """Açıklayıcı ön ekleri nötr hâle getirir (kuralı ima etmesin)."""
    return re.sub(r"^(Düzeltme işaretli kelimeler|Kesmeli eski yazımlar): ", "Şu kelimeler: ", metin)


maddeler = []
katman_haric = []
for x in a:
    if x.get("katman_farki"):
        katman_haric.append(x["no"])
        continue
    maddeler.append({
        "kaynak_no": x["no"],
        "kitap": x["kitap"],
        "sayfa_no": x["sayfa_no"],
        "yazim": notr(x["kitaptaki"]),
        "baglam": a_baglam[x["no"]],
    })

for x in json.load(open(V / "B_anahtar.json", encoding="utf-8")):
    if x.get("katman_farki"):
        katman_haric.append(x["no"])
        continue
    maddeler.append({
        "kaynak_no": x["no"],
        "kitap": x["kitap"],
        "sayfa_no": x["sayfa_no"],
        "yazim": x["parca"],
        "baglam": x["baglam"],
    })

r = random.Random(TOHUM)
r.shuffle(maddeler)
for i, m in enumerate(maddeler, 1):
    m["kimlik"] = f"K{i:03d}"

json.dump(maddeler, open(V / "kurul_anahtar.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

toplam_sayi = len(maddeler)

TALIMAT = f"""Aşağıda Türkçe ders kitaplarından (MEB) alınmış {toplam_sayi} aday var. Her aday, kitapta yazım ya da noktalama hatası olabilecek bir yer. Bazıları gerçekten hata, bazıları değil. Görevin her biri için karar vermek. Ölçü: TDK Yazım Kılavuzu (güncel) ve Güncel Türkçe Sözlük.

Her satırda: kimlik, kitap ve sayfa, kitaptaki yazım (« » içinde; birden çok kelime verilmişse hepsi aynı sayfada ve aynı türden) ve metindeki çevresi.

KARAR SEÇENEKLERİ (yalnız birini yaz):
- HATA: Kitapta gerçekten yanlış yazılmış ya da noktalanmış.
- HATA DEĞİL: Doğru yazım (terim, özel ad, yabancı kelime, kısaltma, birim, formül dahil) ya da TDK'ya göre kabul edilebilir bir tercih.
- HATA DEĞİL (alıntı): Şiir, eski metin, halk ağzı ya da imzalı bir yazarın metni içinde; yazım, yazarın ya da dönemin özgün yazımı. MEB kuralı: bu farklar hata sayılmaz ve düzeltilmez.
- HATA DEĞİL (PDF): Metin PDF'ten çıkarılırken bozulmuş gibi görünüyor (harf kayması, özel işaret, satır sonunda bölünmüş kelime); basılı kitapta büyük ihtimalle sorun yok.
- EMİN DEĞİLİM: Bağlam yetmiyor ya da kural gerçekten tartışmalı.

ÖNEMLİ KURAL: Alıntı içinde olsa bile DİZGİ KAZASI hatadır: yanlış harf ya da rakam dizilmesi (O harfi yerine 0, küçük l yerine büyük I gibi), ters tırnak, kelime içine yanlışlıkla girmiş harf. Bunlara HATA de. Alıntıda yalnız yazarın/dönemin bilinçli yazım farkları (düzeltme işareti, eski kelime biçimi, eski kesme kullanımı vb.) HATA DEĞİL (alıntı) sayılır.

Diğer kurallar:
- Yalnız « » içindeki yazımı değerlendir; çevredeki başka şeyleri düzeltme.
- Birden çok kelime verilen satırda: kelimelerin çoğuna göre tek karar ver; ayrı düşünenleri gerekçede yaz.
- Tahmin etme; emin değilsen EMİN DEĞİLİM yaz. Bütün adaylar hata ya da hepsi hata değil olmak zorunda değil.

Cevabını yalnız şu tabloyla ver ({toplam_sayi} satır, sırayı bozma), başka açıklama ekleme. Cevap yarıda kesilirse kaldığın yerden devam edeceğim:
Kimlik | Karar | Alıntı içinde mi? (EVET/HAYIR/BİLİNMİYOR) | Doğrusu (yalnız HATA ise) | Gerekçe (tek kısa cümle)

ADAYLAR:
"""
satirlar = [
    f"{m['kimlik']} | {KITAP_AD[m['kitap']]}, PDF s.{m['sayfa_no']} | Kitaptaki: «{m['yazim']}» | Çevresi: {m['baglam']}"
    for m in maddeler
]
(H / "KURUL_talimat.txt").write_text(TALIMAT + "\n".join(satirlar) + "\n", encoding="utf-8")
print(f"{len(maddeler)} aday (katman farkı nedeniyle kurul dışı bırakılan: {katman_haric}); {len((H / 'KURUL_talimat.txt').read_text(encoding='utf-8'))} karakter")

# Kilit dosyasını A_birlesik_anahtar.json ve kurul_anahtar.json parmak izleriyle güncelle
kilit_yolu = PROJE / "testseti" / "bagimsiz3_kilit.txt"
kilit_metin = kilit_yolu.read_text(encoding="utf-8")
ek_hash = (
    f"{sha256_dosya_lf(V / 'A_birlesik_anahtar.json')} *A_birlesik_anahtar.json\n"
    f"{sha256_dosya_lf(V / 'kurul_anahtar.json')} *kurul_anahtar.json\n"
)
if "*A_birlesik_anahtar.json" not in kilit_metin:
    kilit_metin = kilit_metin.replace("Ön kayıt:", ek_hash + "Ön kayıt:")
    kilit_metin += (
        f"A listesi: ChatGPT (35) ve Gemini (58) sonuçları birleştirildi; 68 aday oluşturuldu (12 dayanaksız/mevcut iddia elendi).\n"
        f"Kurul listesi: A (68 aday) + B (129 katman-temiz aday; 4 katman farkı hariç) = {toplam_sayi} aday tohum {TOHUM} ile karıştırılarak K001-K{toplam_sayi:03d} kimlikleriyle hazırlandı.\n"
    )
    kilit_yolu.write_text(kilit_metin, encoding="utf-8")
    print("bagimsiz3_kilit.txt güncellendi.")
