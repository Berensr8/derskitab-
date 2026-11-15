"""K45 Aşama 2.1: A (ChatGPT + Gemini) bulgularını birleştirir ve metin katmanı kontrolü (K41-ek) uygular."""
import json
import sys
from collections import Counter
from pathlib import Path

import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from k42_katman import katman_farki, sayfa_glif_metni
from k45_ortak import CIKTI, KITAP_AD, PAKET, PROJE

sys.stdout.reconfigure(encoding="utf-8")

H = PAKET
V = CIKTI
C, G, CG = {"chatgpt"}, {"gemini"}, {"chatgpt", "gemini"}

# (sayfa_kodu, kitaptaki, onerilen, neden, kaynak, ara_metin)
M = [
    # S01 (biyoloji12, s.17)
    ("S01", "1953’ te", "1953’te", "Kesme işaretinden sonra gereksiz boşluk", C, "1953’ te"),
    ("S01", "(Görsel 1.2)],1869", "(Görsel 1.2)], 1869", "Virgülden sonra boşluk eksikliği", CG, "(Görsel 1.2)],1869"),
    # S02 (biyoloji12, s.19)
    ("S02", "Deoksiribonukleaz", "deoksiribonükleaz", "Yanlış yazım / büyük harf hatası", G, "Deoksiribonukleaz"),
    ("S02", "Görsel 1.8’ de", "Görsel 1.8’de", "Kesme işaretinden sonra gereksiz boşluk", CG, "Görsel 1.8’ de"),
    # S03 (biyoloji12, s.71)
    ("S03", "Görsel 2.2 ‘de", "Görsel 2.2’de", "Kesme işaretinden önce gereksiz boşluk", CG, "Görsel 2.2 ‘de"),
    (
        "S03",
        "tepkimelerine endergonik tepkimeler, enerji açığa çıkaran tepkimelerine ise",
        "tepkimelere endergonik tepkimeler, enerji açığa çıkaran tepkimelere ise",
        "Yanlış yazım / ek hatası",
        G,
        "tepkimelerine endergonik tepkimeler",
    ),
    # S04 (biyoloji12, s.77)
    ("S04", "karbondioksidi (ve karbondioksit)", "karbon dioksidi / karbon dioksit", "Ayrı yazım hatası (TDK)", G, "karbondioksidi"),
    ("S04", "Engelman deneyi", "Engelmann deneyi", "Yanlış yazım / harf eksikliği", G, "Engelman deneyi"),
    # S05 (biyoloji12, s.78)
    ("S05", "karbondioksit (ve karbondioksittir)", "karbon dioksit / karbon dioksittir", "Ayrı yazım hatası (TDK)", G, "karbondioksit"),
    ("S05", "hidrojen sülfürü", "hidrojen sülfür", "Yanlış yazım", G, "hidrojen sülfürü"),
    ("S05", "Tablo 2.1: Fotosentezde Atomların İzlenmesi", "Tablo 2.1: Fotosentezde atomların izlenmesi", "Büyük harf hatası", G, "Tablo 2.1: Fotosentezde Atomların İzlenmesi"),
    # S06 (biyoloji12, s.88)
    ("S06", "karbondioksitin (ve karbondioksit)", "karbon dioksitin / karbon dioksit", "Ayrı yazım hatası (TDK)", G, "karbondioksitin"),
    # S07 (biyoloji12, s.111)
    ("S07", "gece gündüz fotosentezi", "gece gündüz, fotosentezi", "Virgül eksikliği", C, "gece gündüz fotosentezi"),
    ("S07", "H2S’ dir", "H2S’dir", "Kesme işaretinden sonra gereksiz boşluk", CG, "H2S’ dir"),
    ("S07", "O2 dir", "O2’dir", "Kesme işareti eksikliği", CG, "O2 dir"),
    ("S07", "karbondioksit (ve karbondioksidi)", "karbon dioksit / karbon dioksidi", "Ayrı yazım hatası (TDK)", G, "karbondioksit ve su"),
    ("S07", "Farklı yönleri", "Farklı Yönleri", "Büyük harf hatası (tablo başlığı)", G, "Farklı yönleri"),
    # S08 (biyoloji12, s.116)
    ("S08", "PGAL’nin", "PGAL’in", "Kısaltmaya gelen ek hatası", G, "PGAL’nin"),
    # S10 (biyoloji12, s.137)
    ("S10", "Kloroplast içermez bu yüzden", "Kloroplast içermez, bu yüzden", "Virgül eksikliği", C, "Kloroplast içermez bu yüzden"),
    ("S10", "Yaprağının enine kesitinde", "Yaprağın enine kesitinde", "Yanlış yazım / ek hatası", G, "Yaprağının enine kesitinde"),
    ("S10", "karbondioksitin (ve karbondioksit)", "karbon dioksitin / karbon dioksit", "Ayrı yazım hatası (TDK)", G, "karbondioksitin dışarı"),
    # S11 (biyoloji12, s.164)
    ("S11", "%78’ i", "%78’i", "Kesme işaretinden sonra gereksiz boşluk", CG, "%78’ i"),
    # S12 (biyoloji12, s.165)
    ("S12", "Ksilemdeki su ,", "Ksilemdeki su,", "Virgülden önce gereksiz boşluk", C, "Ksilemdeki su ,"),
    ("S12", "Ksilem de", "Ksilemde", "Bağlaç/ek yazım hatası", G, "Ksilem de fazla"),
    ("S12", "yukarı doğru", "yukarıya doğru", "Yazım / ek tercihi", G, "yukarı doğru itilirken"),
    # S13 (biyoloji12, s.169)
    ("S13", "Deneyin Tasarlanması: 20 dakika, Tasarının sunumu:", "Deneyin tasarlanması: 20 dakika, tasarının sunumu:", "Büyük harf hatası", G, "Deneyin Tasarlanması: 20 dakika, Tasarının sunumu:"),
    # S14 (biyoloji12, s.186)
    ("S14", "meyve- yi", "meyveyi", "Satır sonu / dizgi hatası (tire)", G, "meyve- yi"),
    ("S14", "Oksin hormonun", "Oksin hormonunun", "Yanlış yazım / hece düşmesi", G, "Oksin hormonun"),
    # S15 (biyoloji12, s.190)
    ("S15", "işaretleyiz", "işaretleyiniz", "Harf / hece eksikliği", CG, "işaretleyiz"),
    ("S15", "Triploit", "Triploid", "Yanlış yazım", G, "Triploit"),
    # S16 (inkilap12, s.23)
    ("S16", "içinde..", "içinde...", "Eksik nokta (üç nokta yerine iki nokta)", CG, "içinde.."),
    ("S16", "Evvelâ O gitmek istiyor.", "Evvelâ o gitmek istiyor.", "Gereksiz büyük harf (zamir)", CG, "Evvelâ O gitmek istiyor."),
    ("S16", "ünvanlara", "unvanlara", "Yazım değişimi", G, "ünvanlara"),
    # S17 (inkilap12, s.79)
    ("S17", "İtalyanlara, diğer Ege Adaları Yunanlara", "İtalyanlara, diğer Ege Adaları Yunanlılara", "Özel ad yapım eki", G, "İtalyanlara, diğer Ege Adaları Yunanlara"),
    # S18 (inkilap12, s.87)
    ("S18", "Görsel 2.11: İstiklâl Marşı", "Görsel 2.11: İstiklal Marşı", "Düzeltme işareti kullanımı", G, "Görsel 2.11: İstiklâl Marşı"),
    # S19 (inkilap12, s.117)
    ("S19", "Bugün hepimize düşen ortak görev;", "Bugün hepimize düşen ortak görev:", "Yanlış noktalama işareti", C, "Bugün hepimize düşen ortak görev;"),
    ("S19", "Türk ulusu;", "Türk ulusu,", "Yanlış noktalama işareti", C, "Türk ulusu;"),
    ("S19", "II. Abdülhamit", "II. Abdülhamid", "Özel ad yazımı", G, "II. Abdülhamit"),
    # S20 (inkilap12, s.130)
    ("S20", "Kazım Karabekir;", "Kazım Karabekir", "Gereksiz noktalı virgül", C, "Kazım Karabekir;"),
    ("S20", "Kazım Karabekir", "Kâzım Karabekir", "Düzeltme işareti eksikliği", G, "Kazım Karabekir;"),
    ("S20", "milli hudutları", "millî hudutları", "Düzeltme işareti eksikliği", C, "milli hudutları"),
    ("S20", "dahilinde", "dâhilinde", "Düzeltme işareti eksikliği", C, "dahilinde"),
    ("S20", "milli hakimiyetini", "millî hâkimiyetini", "Düzeltme işareti eksikliği", C, "milli hakimiyetini"),
    ("S20", "milli hakimiyete", "millî hâkimiyete", "Düzeltme işareti eksikliği", C, "milli hakimiyete"),
    ("S20", "Milli istihsalini", "Millî istihsalini", "Düzeltme işareti eksikliği", C, "Milli istihsalini"),
    ("S20", "riya tembellik", "riya, tembellik", "Sıralanan kelimeler arasında virgül eksikliği", C, "riya tembellik"),
    ("S20", "7. milletlere", "milletlere", "Gereksiz madde numarası", C, "7. milletlere"),
    ("S20", "aleyhtar", "aleyhdar", "Özgün metin yazımı", G, "aleyhtar"),
    # S21 (inkilap12, s.141)
    ("S21", "Anayasada", "Anayasa’da", "Kesme işareti eksikliği", C, "Anayasada"),
    ("S21", "Anayasanın", "Anayasa’nın", "Kesme işareti eksikliği", C, "Anayasanın"),
    ("S21", "Türkiye Cumhuriyetine", "Türkiye Cumhuriyeti’ne", "Kesme işareti eksikliği", G, "Türkiye Cumhuriyetine"),
    # S22 (inkilap12, s.150)
    ("S22", "ve tabi bu arada", "ve tabii bu arada", "Yanlış kelime yazımı", C, "ve tabi bu arada"),
    ("S22", "Büyük Millet Meclis", "Büyük Millet Meclisi", "Yanlış yazım / ek eksikliği", G, "Büyük Millet Meclis "),
    # S23 (inkilap12, s.166)
    ("S23", "meyvalar", "meyveler", "Yanlış ünlü kullanımı / eski yazım", CG, "meyvalar"),
    ("S23", "meyvaya", "meyveye", "Yanlış ünlü kullanımı / eski yazım", CG, "meyvaya"),
    # S25 (inkilap12, s.179 — Gemini S24'ün basılı sayfa numarası 178 ile karıştırıp S24 yazdı, metin S25'te)
    ("S25", "Yozıf Sıtalin", "Yozif Stalin", "Okunuş yazımı hatası", G, "Yozıf Sıtalin"),
    ("S25", "Andre Maginot", "André Maginot", "Özel ad yazımı", G, "Andre Maginot"),
    ("S25", "kollektifleştirme", "kolektifleştirme", "Fazladan harf / çift ünsüz", CG, "kollektifleştirme"),
    # S26 (inkilap12, s.182)
    ("S26", "Kızıl Ordunun", "Kızıl Ordu’nun", "Kesme işareti eksikliği", G, "Kızıl Ordunun"),
    # S27 (inkilap12, s.205)
    ("S27", "Demokrat Parti (DP)’nin", "Demokrat Partinin (DP)", "Kesme işaretinin ve ekin konumlandırılması", CG, "Demokrat Parti (DP)’nin"),
    ("S27", "Demokrat Partinin", "Demokrat Parti’nin", "Kesme işareti eksikliği / tutarsızlığı", G, "Demokrat Partinin kurulmasıyla"),
    # S28 (inkilap12, s.224)
    ("S28", "Arap’ın", "Arab’ın", "Ünsüz yumuşaması iddiası", G, "Arap’ın"),
    # S29 (inkilap12, s.262)
    ("S29", "suv modeli", "SUV modeli", "Kısaltmada büyük harf hatası", CG, "suv modeli"),
    ("S29", "COVİD-19", "COVID-19", "Kısaltmada yanlış harf kullanımı", CG, "COVİD-19"),
    # S30 (inkilap12, s.273)
    ("S30", "Balkanlara", "Balkanlar’a", "Kesme işareti eksikliği", C, "Balkanlara"),
    ("S30", "Yarımada’yı", "yarımadayı", "Gereksiz büyük harf ve kesme işareti", C, "Yarımada’yı"),
    ("S30", "Kafkaslarda", "Kafkaslar’da", "Kesme işareti eksikliği", C, "Kafkaslarda"),
    ("S30", "Yurtdışı Türkler", "Yurt Dışı Türkler", "Kurum adı yazımı (yurt dışı ayrı)", G, "Yurtdışı Türkler"),
]

# Yapay zekânın önerdiği yazım kitapta zaten mevcut olan (veya doğru olduğunu belirttiği) dayanaksız maddeler:
ATLANAN = [
    "S02 bakterisiv ve (G - kitapta zaten 'bakterisi ve' yazılı)",
    "S06 Ba(OH)2' (G - kitapta zaten 'Ba(OH)2,' yazılı)",
    "S06 Grafik 2.4: CO, yoğunluğunun (G - kitapta zaten 'Grafik 2.4: CO2 yoğunluğunun' yazılı)",
    "S09 Floem (G - kitapta zaten 'Floem' yazılı, öneriyle aynı)",
    "S09 325000'den (G - kitapta zaten '325 000’den' yazılı)",
    "S11 Mantar hif leri (G - kitapta zaten 'Mantar hifleri' yazılı)",
    "S18 Hükûmetinin / Hükümetini / Hükûmeti (G - S18'deki tüm geçmeler zaten 'Hükûmetini' / 'Hükûmeti' yazılı)",
    "S18 Büyük Millet Meclis (G - S18'de tüm geçmeler 'Büyük Millet Meclisi/Meclisinde/Meclisince'; eksik ekli olan S22'de)",
    "S20 dünyanin sulh (G - kitapta zaten 'dünyanın sulh' yazılı)",
    "S22 hükümetin (G - kitapta zaten 'hükûmetin' yazılı)",
    "S27 Türkiye Büyük Millet Meclisinde (G - öneriyle aynı, 'TDK doğru' notu)",
    "S29 Erciyes Üniversitesinde (G - öneriyle aynı, 'TDK doğru' notu)",
]

sayfalar = {x["kod"]: x for x in json.load(open(H / "A_sayfa_listesi.json", encoding="utf-8"))}
pdfler = {k: pymupdf.open(PROJE / "veri" / f"{k}.pdf") for k in ("biyoloji12", "inkilap12")}
glif_map = {kod: sayfa_glif_metni(pdfler[v["kitap"]][v["sayfa_no"] - 1]) for kod, v in sayfalar.items()}

metin = {}
for parca in open(H / "A_30_sayfa_metin.txt", encoding="utf-8").read().split("===== ")[1:]:
    metin[parca[:3]] = " ".join(parca.split("=====", 1)[1].split())

wb = Workbook()
ws = wb.active
ws.title = "A - Bulunanlar"
ws.append([
    "No", "Sayfa kodu", "Kitap, PDF sayfa", "A_30_sayfa.pdf'te kaçıncı sayfa", "Kitaptaki yazım",
    "Önerilen doğrusu", "Neden hata olabilir (yapay zekânın gerekçesi)", "Metinde geçtiği yer", "Kararın", "Notun"
])
for c in ws[1]:
    c.font = Font(bold=True)
    c.fill = PatternFill("solid", fgColor="E8E2D4")

anahtar, bulunamayan, katman_farklari = [], [], []
for i, (kod, kitaptaki, oneri, neden, kaynak, ara) in enumerate(M, 1):
    s = sayfalar[kod]
    m = metin.get(kod, "")
    j = m.find(ara)
    yer = (("…" if j > 80 else "") + m[max(0, j - 80):j + len(ara) + 80] + "…") if j >= 0 else "(PDF metninde bulunamadı; sayfaya bakın)"
    if j < 0:
        bulunamayan.append((kod, ara))
    kf = katman_farki(glif_map[kod], ara)
    if kf:
        katman_farklari.append((f"A{i:02d}", kod, kitaptaki, kf))
    no = f"A{i:02d}"
    ws.append([no, kod, f"{KITAP_AD[s['kitap']]}, PDF s.{s['sayfa_no']}", int(kod[1:]), kitaptaki, oneri, neden, yer, "", ""])
    anahtar.append({
        "no": no,
        "sayfa": kod,
        "kitap": s["kitap"],
        "sayfa_no": s["sayfa_no"],
        "kitaptaki": kitaptaki,
        "onerilen": oneri,
        "kaynak": sorted(kaynak),
        "katman_farki": kf,
    })

dv = DataValidation(type="list", formula1='"Hata,Hata değil (alıntı/yazarın yazımı),Hata değil,Emin değilim"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"I2:I{len(M) + 1}")

for col, w in zip("ABCDEFGHIJ", (6, 8, 20, 10, 34, 30, 34, 70, 22, 26)):
    ws.column_dimensions[col].width = w

for row in ws.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    row[8].fill = PatternFill("solid", fgColor="FFF4C2")

ws.freeze_panes = "A2"
wb.save(H / "A_benim_kararlarim.xlsx")

(V / "A_birlesik_anahtar.json").write_text(
    json.dumps({"maddeler": anahtar, "atlanan": ATLANAN}, ensure_ascii=False, indent=1),
    encoding="utf-8"
)

print(len(M), "madde;", Counter("+".join(sorted(x[4])) for x in M))
print("metinde bulunamayan:", bulunamayan)
print("A katman farkı:", katman_farklari)
