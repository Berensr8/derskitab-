"""A: ChatGPT + Gemini bulgularını birleştirir; Beren'in karar Excel'i. Kim buldu / emin mi gizli tutulur."""
import json, sys
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

H = Path("bagimsiz_degerlendirme")
C, G, CG = {"chatgpt"}, {"gemini"}, {"chatgpt", "gemini"}
# (sayfa, kitaptaki, önerilen, neden, kaynak, aranan)
M = [
 ("S01", "ZARARLI VEYA TAHRIŞ EDICI MADDE", "ZARARLI VEYA TAHRİŞ EDİCİ MADDE", "Büyük İ yerine I kullanılmış", G, "TAHRI"),
 ("S02", "\"anlat bakalım\"", "\"Anlat Bakalım\"", "Oyun adı büyük harfle yazılmalı", G, "anlat bakal"),
 ("S02", "1. Ve 2. Soruları", "1 ve 2. soruları", "Cümle ortasında büyük harf", G, "Ve 2"),
 ("S05", "kazanır. (Görsel 1.26).", "kazanır (Görsel 1.26).", "Parantezden önce gereksiz nokta", CG, "(Görsel 1.26)"),
 ("S06", "Yağ asiti", "Yağ asidi", "Ünsüz yumuşaması (asit → asidi)", CG, "asiti"),
 ("S07", "200 ml", "200 mL", "Mililitre kısaltması", G, "200 ml"),
 ("S07", "gözlük, önlük", "gözlük, önlük.", "Sonda nokta eksik", G, "önlük"),
 ("S09", "molekullerinin (2 yerde)", "moleküllerinin", "ü yerine u", CG, "molekullerin"),
 ("S09", "secici", "seçici", "ç yerine c", CG, "secici"),
 ("S09", "gecirgen", "geçirgen", "ç yerine c", CG, "gecirgen"),
 ("S09", "gecişidir", "geçişidir", "ç yerine c", CG, "gecişidir"),
 ("S09", "yuksek", "yüksek", "ü yerine u", CG, "yuksek"),
 ("S10", "4. Zorlandığınız konularla … kullandığım yöntemler", "Zorlandığım konularla", "Kişi eki uyumsuz (sizin / benim)", G, "Zorlandığınız"),
 ("S12", "eşik şiddetten", "eşik şiddetinden", "Ek eksik", G, "eşik şiddet"),
 ("S13", "ilgili kas tepki veremez", "ilgili kas tepki veremez.", "Bilgi kutusu sonunda nokta eksik", G, "tepki veremez"),
 ("S16", "“Analitik Dereceli Puanlama Anahtarı’’", "“Analitik Dereceli Puanlama Anahtarı”", "Kapanış tırnağı yerine iki tek tırnak", G, "Puanlama Anahtar"),
 ("S16", "Etkileşimli  Videosu (iki boşluk)", "Etkileşimli Videosu", "Fazla boşluk", G, "Etkileşimli"),
 ("S21", "velakin", "velâkin", "Düzeltme işareti eksik", G, "velakin"),
 ("S22", "yararlanılamıyacak", "yararlanılamayacak", "Ek yanlış yazılmış", CG, "yararlanılam"),
 ("S22", "tesbit", "tespit", "Ünsüz yazımı (tesbit → tespit)", CG, "tesbit"),
 ("S22", "câridir", "caridir", "Gereksiz düzeltme işareti", CG, "câri"),
 ("S24", "Düzeltme işaretli kelimeler: lâf, lâzımdır, tevârüt, lâtif, zarâfet, elâ, Mûsikileri, şahsî, sehl-i mümtenî",
  "laf, lazımdır, tevarüt, latif, zarafet, ela, Musikileri, şahsi, sehl-i mümteni", "Gereksiz düzeltme işareti (hepsi aynı kural)", CG, "lâf"),
 ("S24", "halde", "hâlde", "Düzeltme işareti eksik", G, "halde"),
 ("S24", "bir çok", "birçok", "Bitişik yazılmalı", CG, "bir çok"),
 ("S24", "”Yüce dağların başında …”", "“Yüce dağların başında …”", "Açılış tırnağı ters", CG, "Yüce da"),
 ("S24", "dört nala", "dörtnala", "Bitişik yazılmalı", G, "dört nala"),
 ("S24", "kayaIıklar", "kayalıklar", "Küçük l yerine büyük I dizilmiş", CG, "kayaI"),
 ("S24", "mısraı", "mısrası", "İyelik eki", CG, "mısraı"),
 ("S24", "Cenab’ın", "Cenap’ın", "Özel adın yazımı", C, "Cenab"),
 ("S24", "Dranas’ın", "Dıranas’ın", "Özel adın yazımı (Ahmet Muhip Dıranas)", CG, "Dranas"),
 ("S25", "ASYANIN KANDİLLERİ", "ASYA’NIN KANDİLLERİ", "Özel ada gelen ekte kesme eksik", G, "ASYANIN"),
 ("S25", "0 civar karyelerinden", "O civar karyelerinden", "O harfi yerine 0 rakamı", CG, "civar karyeler"),
 ("S25", "Düzeltme işaretli kelimeler: Yûnus, Nihâyet, kerâmet, inâyetlerini, Velî, Bektâş, muâmele, misâfir, Gâfil, lâkin, hatânın, pişmân, derhâl, kusûrunu, cevâbı",
  "Yunus, Nihayet, keramet, inayetlerini, Veli, Bektaş, muamele, misafir, Gafil, lakin, hatanın, pişman, derhal, kusurunu, cevabı", "Gereksiz düzeltme işareti (hepsi aynı kural)", CG, "Nihâyet"),
 ("S25", "Kesmeli eski yazımlar: def’a, i’tiraf, ta’yin, pîr’in / pîr’e", "defa, itiraf, tayin, pirin / pire", "Gereksiz kesme işareti", CG, "def"),
 ("S25", "mikdar", "miktar", "Eski yazım (mikdar → miktar)", CG, "mikdar"),
 ("S25", "lûtf", "lütuf", "Eski yazım", CG, "lûtf"),
 ("S25", "dânesine", "tanesine", "Eski yazım", CG, "dânesine"),
 ("S25", "nefs edeyim", "nefes edeyim", "Eski yazım", G, "nefs edeyim"),
 ("S25", "… edeyim” dedi. (2 yerde: nefs edeyim, himmet edeyim)", "… edeyim.” dedi.", "Tırnak içindeki cümlenin sonunda nokta eksik", G, "himmet edeyim"),
 ("S27", "bıçak?..", "bıçak?...", "Noktalama", G, "bıçak?"),
 ("S27", "Düzeltme işaretli kelimeler: Eflâtun, pervâneleri", "Eflatun, pervaneleri", "Gereksiz düzeltme işareti", G, "Eflâtun"),
 ("S27", "Meş’aleler / meş’aleler", "Meşaleler / meşaleler", "Gereksiz kesme işareti", G, "eş’ale"),
 ("S27", "halinde", "hâlinde", "Düzeltme işareti eksik", G, "halinde"),
 ("S28", "sadef", "sedef", "Eski yazım", G, "sadef"),
 ("S28", "Nisan mevsiminde / Nisan yağmurunun", "nisan mevsiminde / nisan yağmurunun", "Belirli tarih bildirmeyen ay adı küçük yazılır", CG, "Nisan"),
 ("S28", "ızdırap", "ıstırap", "Yazım (ızdırap → ıstırap)", G, "ızdırap"),
 ("S28", "lâyık", "layık", "Gereksiz düzeltme işareti", CG, "lâyık"),
 ("S29", "DINLEME/İZLEME", "DİNLEME/İZLEME", "Büyük İ yerine I kullanılmış", G, "DINLEME"),
 ("S29", "Milli (MİLLİ EDEBİYAT, Milli Edebiyat, Milli Mücadele’nin, Milli Mücadele ile / de)", "Millî", "Nispet î'sinde düzeltme işareti eksik (hepsi aynı kural)", CG, "illi"),
 ("S29", "Milli Edebiyat dönemi", "Millî Edebiyat Dönemi", "Dönem adı büyük harfle (2 yerde)", CG, "Edebiyat dönemi"),
 ("S29", "dışardan", "dışarıdan", "Ünlü düşmesi", CG, "dışardan"),
 ("S29", "Türk Edebiyatı", "Türk edebiyatı", "Cins ad küçük yazılır", C, "Türk Edebiyat"),
 ("S30", "Balkan Savaşlarına", "Balkan Savaşları’na", "Özel ada gelen ekte kesme eksik", G, "Balkan Sava"),
 ("S30", "belâ", "bela", "Gereksiz düzeltme işareti", G, "belâ"),
 ("S30", "Ocean Zırhlısı’na / Ocean Zırhlısı’nın", "Ocean zırhlısına / Ocean zırhlısının", "Tür adı küçük yazılır, kesme gereksiz", G, "Zırhlısı"),
 ("S30", "çevirip, ateşlediler", "çevirip ateşlediler", "Zarf-fiilden sonra gereksiz virgül", G, "çevirip"),
 ("S30", "getirip, namluya", "getirip namluya", "Zarf-fiilden sonra gereksiz virgül", G, "getirip"),
 ("S30", "“Besmele”", "“besmele”", "Cins ad küçük yazılır", G, "Besmele"),
 ("S30", "Mehmed Hilmi", "Mehmet Hilmi", "Özel adın yazımı", G, "Mehmed"),
 ("S30", "Ali yardım et", "Ali, yardım et", "Hitaptan sonra virgül", C, "Ali yard"),
 ("S30", "Yarabbi", "Ya Rabbi", "Ayrı yazılmalı", C, "Yarabbi"),
 ("S30", "aferin Seyit", "aferin, Seyit", "Hitaptan önce virgül", C, "aferin Seyit"),
]
# Yapay zekânın "doğrusu" kitaptakiyle aynı olduğu (hata iddiası olmayan) maddeler alınmadı:
ATLANAN = ["S22 ilmî (G)", "S24 Elhân-ı Şitâ’sından (G)", "S24 sanatkârlarının (G)", "S30 Çanakkale Boğazı’ndan (G)"]

sayfalar = {x["kod"]: x for x in json.load(open(H / "A_sayfa_listesi.json", encoding="utf-8"))}
metin = {}
for parca in open(H / "A_30_sayfa_metin.txt", encoding="utf-8").read().split("===== ")[1:]:
    metin[parca[:3]] = " ".join(parca.split("=====", 1)[1].split())
AD = {"biyoloji9": "Biyoloji 9", "biyoloji11": "Biyoloji 11", "turkdili10": "TDE 10"}

wb = Workbook(); ws = wb.active; ws.title = "A - Bulunanlar"
ws.append(["No", "Sayfa kodu", "Kitap, PDF sayfa", "A_30_sayfa.pdf'te kaçıncı sayfa", "Kitaptaki yazım",
           "Önerilen doğrusu", "Neden hata olabilir (yapay zekânın gerekçesi)", "Metinde geçtiği yer", "Kararın", "Notun"])
for c in ws[1]:
    c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="E8E2D4")
anahtar, bulunamayan = [], []
for i, (kod, kitaptaki, oneri, neden, kaynak, ara) in enumerate(M, 1):
    s = sayfalar[kod]; m = metin.get(kod, "")
    j = m.find(ara)
    yer = (("…" if j > 80 else "") + m[max(0, j - 80):j + len(ara) + 80] + "…") if j >= 0 else "(PDF metninde bulunamadı; sayfaya bakın)"
    if j < 0:
        bulunamayan.append((kod, ara))
    no = f"A{i:02d}"
    ws.append([no, kod, f"{AD[s['kitap']]}, PDF s.{s['sayfa_no']}", int(kod[1:]), kitaptaki, oneri, neden, yer, "", ""])
    anahtar.append({"no": no, "sayfa": kod, "kitap": s["kitap"], "sayfa_no": s["sayfa_no"], "kitaptaki": kitaptaki,
                    "onerilen": oneri, "kaynak": sorted(kaynak)})
dv = DataValidation(type="list", formula1='"Hata,Hata değil (alıntı/yazarın yazımı),Hata değil,Emin değilim"', allow_blank=True)
ws.add_data_validation(dv); dv.add(f"I2:I{len(M) + 1}")
for col, w in zip("ABCDEFGHIJ", (6, 8, 20, 10, 34, 30, 34, 70, 22, 26)):
    ws.column_dimensions[col].width = w
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    row[8].fill = PatternFill("solid", fgColor="FFF4C2")
ws.freeze_panes = "A2"
wb.save(H / "A_benim_kararlarim.xlsx")
Path("veri/bagimsiz/A_birlesik_anahtar.json").write_text(
    json.dumps({"maddeler": anahtar, "atlanan": ATLANAN}, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(M), "madde;", Counter("+".join(sorted(x[4])) for x in M))
print("metinde bulunamayan:", bulunamayan)
