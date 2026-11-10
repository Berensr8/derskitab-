"""A: ChatGPT + Gemini bulgularını birleştirir; Beren'in karar Excel'i. Kim buldu / emin mi gizli tutulur."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

H = Path("bagimsiz_degerlendirme2")
V = Path("veri/bagimsiz2")
C, G, CG = {"chatgpt"}, {"gemini"}, {"chatgpt", "gemini"}

# (sayfa_kodu, kitaptaki, onerilen, neden, kaynak, ara_metin)
M = [
    # S01
    ("S01", "tartışı- .", "tartışınız.", "Eksik harf / dizgi hatası", G, "tartış"),
    # S02
    ("S02", "Form11", "Form 11", "Eksik boşluk", CG, "Form11"),
    ("S02", "menekşe rengi", "Menekşe rengi", "Küçük harf (tablo hücresi)", CG, "menekşe rengi"),
    ("S02", "Commasie", "Coomassie", "Yanlış yazılmış kelime", G, "Commasie"),
    # S03
    ("S03", "yazınız..", "yazınız.", "Fazladan nokta", CG, "yazınız.."),
    # S06
    ("S06", "Kuşlar;", "Kuşlar", "Noktalı virgül kullanımı", C, "Kuşlar;"),
    ("S06", "coğrafik", "coğrafi", "Yanlış yazılmış kelime", G, "coğrafik"),
    # S07
    ("S07", "Yönerge :", "Yönerge:", "İki noktadan önce gereksiz boşluk", C, "Yönerge :"),
    # S08
    ("S08", "11,12, 13", "11, 12, 13", "Virgülden sonra eksik boşluk", CG, "11,12,"),
    ("S08", "Canis familaris", "Canis familiaris", "Eksik harf", G, "Canis familaris"),
    ("S08", "Canidea", "Canidae", "Harfler yer değiştirmiş", G, "Canidea"),
    # S10
    ("S10", "Günlük;", "Günlük,", "Noktalama işareti", C, "Günlük;"),
    ("S10", "hiç kurulmamış.", "hiç kurulmamıştır.", "Eksik ek", G, "hiç kurulmamış"),
    # S18
    ("S18", "akıllı termostatlar;", "akıllı termostatlar", "Gereksiz noktalı virgül", C, "akıllı termostatlar;"),
    ("S18", "örnek veriniz?", "örnek veriniz.", "Yanlış soru işareti", CG, "örnek veriniz?"),
    ("S18", "algılayıp,", "algılayıp", "Zarf-fiilden sonra gereksiz virgül", G, "algılayıp,"),
    # S19
    ("S19", "Kap atışı", "Kalp atışı", "Eksik harf", CG, "Kap atışı"),
    # S20
    ("S20", "solunum hızı;", "solunum hızı,", "Yanlış noktalı virgül", C, "solunum hızı;"),
    # S21
    ("S21", "ESKİ SARAYI YAPTIĞINI BİLDİRİR (ve Eski Sarayı Yaptığını Bildirir)", "ESKİ SARAY’I YAPTIĞINI BİLDİRİR", "Özel ada gelen ekte kesme eksik", C, "ESKİ SARAYI"),
    ("S21", "lâtifdir", "latiftir", "Düzeltme işareti ve ünsüz benzeşmesi", G, "lâtifdir"),
    ("S21", "kilârcıbaşı", "kilerci başı", "Yanlış yazım ve bitişik yazım", G, "kilârcıbaşı"),
    ("S21", "sakabaşı", "saka başı", "Bitişik yazım", G, "sakabaşı"),
    ("S21", "gr", "g", "Kısaltma yazımı", G, "gr"),
    ("S21", "nâzırı", "nazırı", "Gereksiz düzeltme işareti", G, "nâzırı"),
    ("S21", "balmumları", "bal mumları", "Bitişik yazım", G, "balmumları"),
    ("S21", "Seyahatnâmesi", "Seyahatnamesi", "Gereksiz düzeltme işareti", G, "Seyahatnâmesi"),
    # S23
    ("S23", "göktaşını (ve göktaşından)", "gök taşını", "Bitişik yazım", G, "göktaşını"),
    ("S23", "aramışlar, ama", "aramışlar ama", "Bağlaçtan önce gereksiz virgül", G, "aramışlar, ama"),
    # S24
    ("S24", "bir takım vasıflar", "birtakım vasıflar", "Bitişik yazılması gereken kelime", CG, "bir takım"),
    # S25
    ("S25", "etdi", "etti", "Eski metin / ünsüz benzeşmesi", CG, "etdi"),
    ("S25", "Çekdim", "Çektim", "Eski metin / ünsüz benzeşmesi", CG, "Çekdim"),
    ("S25", "kabûl", "kabul", "Gereksiz düzeltme işareti", CG, "kabûl"),
    ("S25", "dedigin", "dediğin", "Eski metin / harf farkı", CG, "dedigin"),
    ("S25", "gavga", "kavga", "Eski metin / harf farkı", CG, "gavga"),
    ("S25", "fâ’ide", "fayda", "Eski metin / özgün yazım", G, "fâ"),
    ("S25", "’abesdir", "abestir", "Eski metin / ünsüz benzeşmesi", G, "abesdir"),
    ("S25", "âteşlere", "ateşlere", "Gereksiz düzeltme işareti", G, "âteşlere"),
    ("S25", "sevdâda", "sevdada", "Gereksiz düzeltme işareti", G, "sevdâda"),
    ("S25", "ana", "ona", "Eski metin / özgün yazım", G, " ana "),
    ("S25", "manâ", "mana", "Gereksiz düzeltme işareti", G, "manâ"),
    ("S25", "koçlarun", "koçların", "Eski metin / özgün yazım", G, "koçlarun"),
    ("S25", "devrânıdur", "devranıdır", "Eski metin / özgün yazım", G, "devrânıdur"),
    ("S25", "demün", "demin", "Eski metin / özgün yazım", G, "demün"),
    ("S25", "hayrânıdur", "hayranıdır", "Eski metin / özgün yazım", G, "hayrânıdur"),
    ("S25", "toğan", "doğan", "Eski metin / özgün yazım", G, "toğan"),
    ("S25", "yire", "yere", "Eski metin / özgün yazım", G, "yire"),
    ("S25", "erinün", "erinin", "Eski metin / özgün yazım", G, "erinün"),
    ("S25", "seyrânıdur", "seyranıdır", "Eski metin / özgün yazım", G, "seyrânıdur"),
    # S26
    ("S26", "şunu da,", "şunu da", "da bağlacından sonra gereksiz virgül", G, "şunu da,"),
    # S27
    ("S27", "Sözlü alarak ifade ediniz.", "Sözlü olarak ifade ediniz.", "Harf hatası (alarak -> olarak)", CG, "Sözlü alarak"),
    ("S27", "başdöndürücü", "baş döndürücü", "Bitişik yazım hatası", CG, "başdöndürücü"),
    ("S27", "apartımanlar", "apartmanlar", "Fazla harf / eski yazım", CG, "apartımanlar"),
    ("S27", "hakim", "hâkim", "Düzeltme işareti eksik", CG, "hakim"),
    ("S27", "mimarî", "mimari", "Gereksiz düzeltme işareti", CG, "mimarî"),
    ("S27", "içsıkıntısına", "iç sıkıntısına", "Bitişik yazım hatası", CG, "içsıkıntısına"),
    ("S27", "Murat Beyin", "Murat Bey’in", "Özel ada gelen ekte kesme eksik", G, "Murat Beyin"),
    ("S27", "ne kendileri, ne misafirleri", "ne kendileri ne misafirleri", "Bağlaç arasında gereksiz virgül", G, "ne kendileri, ne misafirleri"),
    ("S27", "bitip,", "bitip", "Zarf-fiilden sonra gereksiz virgül", G, "bitip,"),
    ("S27", "uymamış”", "uymamış.”", "Tırnak içi nokta eksik", G, "uymamış”"),
    # S29
    ("S29", "serhatte", "serhatta", "Ek yazımı / ünlü uyumu", C, "serhatte"),
    ("S29", "dolayıdır, ki", "dolayıdır ki", "ki bağlacından önce gereksiz virgül", CG, "dolayıdır, ki"),
    ("S29", "Südünü", "Sütünü", "Eski metin / ünsüz yumuşaması", CG, "Südünü"),
    ("S29", "Yoğimiş", "Yok imiş", "Bitişik / özgün yazım", CG, "Yoğimiş"),
    ("S29", "İslâm", "İslam", "Gereksiz düzeltme işareti", G, "İslâm"),
    ("S29", "çevrilsin de,", "çevrilsin de", "de bağlacından sonra gereksiz virgül", G, "çevrilsin de,"),
    ("S29", "ki,", "ki", "ki bağlacından sonra gereksiz virgül", G, "ki,"),
    ("S29", "bulunsun da,", "bulunsun da", "da bağlacından sonra gereksiz virgül", G, "bulunsun da,"),
    ("S29", "addetmektir”", "addetmektir.”", "Tırnak içi nokta eksik", G, "addetmektir”"),
    ("S29", "âteşlerini", "ateşlerini", "Gereksiz düzeltme işareti", G, "âteşlerini"),
    ("S29", "mâderini", "maderini", "Gereksiz düzeltme işareti", G, "mâderini"),
    ("S29", "ni’metini", "nimetini", "Eski yazım / kesme", G, "metini"),
    ("S29", "helâl", "helal", "Gereksiz düzeltme işareti", G, "helâl"),
    # S30
    ("S30", "Evlâtlarım", "Evlatlarım", "Gereksiz düzeltme işareti", C, "Evlâtlarım"),
    ("S30", "silâh", "silah", "Gereksiz düzeltme işareti", CG, "silâh"),
    ("S30", "nâzil", "nazil", "Gereksiz düzeltme işareti", CG, "nâzil"),
    ("S30", "İstiklâl (İstiklâl Savaşı’na / İstiklâl Mücadelesi’nin)", "İstiklal", "Gereksiz düzeltme işareti", CG, "İstiklâl"),
    ("S30", "yâdigârıdır", "yadigârıdır", "Gereksiz düzeltme işareti", CG, "yâdigârıdır"),
    ("S30", "döğüşe", "dövüşe", "Harf hatası / eski yazım", CG, "döğüşe"),
    ("S30", "1947,1962", "1947, 1962", "Virgülden sonra eksik boşluk", C, "1947,1962"),
    ("S30", "dolaşırken,", "dolaşırken", "Zarf-fiilden sonra gereksiz virgül", G, "dolaşırken,"),
    ("S30", "tarihi ruhu", "tarihî ruhu", "Nispet î'sinde düzeltme işareti eksik", G, "tarihi ruhu"),
    ("S30", "yoksul, ama", "yoksul ama", "Bağlaçtan önce gereksiz virgül", G, "yoksul, ama"),
]

# Yapay zekânın önerdiği yazım kitapta zaten mevcut olan (hata iddiası dayanaksız) maddeler:
ATLANAN = [
    "S24 herhalde (G - kitapta zaten 'herhâlde' yazılı)",
    "S28 milli (G - kitapta zaten 'Millî' / 'millî' yazılı)",
]

sayfalar = {x["kod"]: x for x in json.load(open(H / "A_sayfa_listesi.json", encoding="utf-8"))}
metin = {}
for parca in open(H / "A_30_sayfa_metin.txt", encoding="utf-8").read().split("===== ")[1:]:
    metin[parca[:3]] = " ".join(parca.split("=====", 1)[1].split())

AD = {"biyoloji9": "Biyoloji 9", "biyoloji11": "Biyoloji 11", "turkdili10": "TDE 10"}

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

anahtar, bulunamayan = [], []
for i, (kod, kitaptaki, oneri, neden, kaynak, ara) in enumerate(M, 1):
    s = sayfalar[kod]
    m = metin.get(kod, "")
    j = m.find(ara)
    yer = (("…" if j > 80 else "") + m[max(0, j - 80):j + len(ara) + 80] + "…") if j >= 0 else "(PDF metninde bulunamadı; sayfaya bakın)"
    if j < 0:
        bulunamayan.append((kod, ara))
    no = f"A{i:02d}"
    ws.append([no, kod, f"{AD[s['kitap']]}, PDF s.{s['sayfa_no']}", int(kod[1:]), kitaptaki, oneri, neden, yer, "", ""])
    anahtar.append({
        "no": no,
        "sayfa": kod,
        "kitap": s["kitap"],
        "sayfa_no": s["sayfa_no"],
        "kitaptaki": kitaptaki,
        "onerilen": oneri,
        "kaynak": sorted(kaynak)
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
