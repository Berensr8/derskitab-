"""K49 Aşama 2.1: A (ChatGPT + Gemini) bulgularını birleştirir ve metin katmanı kontrolü (K41-ek) uygular.

Kaynak dosyalar (kullanıcı kaydetti): bagimsiz_degerlendirme4/gpt.txt (sekmeli tablo) ve gemini.txt (sütun
ayraçları kopyalarken kaybolmuş; maddeler elle ayrıldı). Ön kayda göre A okuyucuları ChatGPT ve Gemini'dir;
kullanıcının ayrıca kaydettiği deepseek.txt (yalnız S01-S06, yarıda kesik) kullanılmaz.

Birleştirme K45 ile aynı: aynı yer için iki modelin maddesi tek madde olur; kitaptaki yazımı sayfa metninde
bulunamayan ya da önerisi kitaptakiyle aynı olan maddeler "dayanaksız" sayılıp atlanır (gerekçesiyle listelenir).
Hata olup olmadığına burada karar verilmez; o kurulun işi.
"""
import json
import sys

import pymupdf

from k42_katman import katman_farki, sayfa_glif_metni
from k49_ortak import CIKTI, KITAP_AD, PAKET, PROJE

sys.stdout.reconfigure(encoding="utf-8")
C, G, CG = {"chatgpt"}, {"gemini"}, {"chatgpt", "gemini"}

# (sayfa, kitaptaki, önerilen, kaynak, sayfa metninde aranacak parça)
M = [
    ("S01", "halleriyle", "hâlleriyle", C, "halleriyle"),
    ("S01", "liste halinde", "liste hâlinde", C, "liste halinde"),
    ("S01", "özelikleri", "özellikleri", CG, "özelikleri"),
    ("S03", "resmi vesikaya", "resmî vesikaya", C, "resmi vesikaya"),
    ("S03", "mühime defterleri", "mühimme defterleri", CG, "mühime defterleri"),
    ("S03", "vaka-i nüvist", "vakanüvis", CG, "vaka-i nüvist"),
    ("S03", "derinlerinde", "derinliklerinde", G, "derinlerinde"),
    ("S06", "Çatalhöyük neolitik yerleşim yeri", "Çatalhöyük Neolitik yerleşim yeri", C, "Çatalhöyük neolitik yerleşim yeri"),
    ("S07", "sürdürülüyor.Höyükteki", "sürdürülüyor. Höyükteki", C, "sürdürülüyor.Höyükteki"),
    ("S07", "Neolitik döneme", "Neolitik Dönem'e", C, "Neolitik döneme"),
    ("S07", "var.'Dedeoğlu", "var.' Dedeoğlu", C, "var.'Dedeoğlu"),
    ("S07", "aktardı.Çok", "aktardı. Çok", CG, "aktardı.Çok"),  # Gemini 'aktardıklarını.Çok' yazdı; kitapta 'aktardı.Çok'
    ("S07", "Değirmencioğlu, 2018*", "Değirmencioğlu, 2018.*", C, "Değirmencioğlu, 2018*"),
    ("S08", "Mahkumların", "Mahkûmların", C, "Mahkumların"),
    ("S08", "mahkumların", "mahkûmların", C, "'mahkumların"),
    ("S09", "techizatları", "teçhizatları", C, "techizatları"),
    ("S10", "Hasan Öğretmenin", "Hasan Öğretmen'in", C, "Hasan Öğretmenin"),
    ("S11", "Avrupa Hun Devletiyle", "Avrupa Hun Devleti'yle", CG, "Avrupa Hun Devletiyle"),
    ("S12", "top-yekûn", "topyekûn", C, "top-yekûn"),
    ("S12", "seferberlik halinde", "seferberlik hâlinde", C, "seferberlik halinde"),
    ("S12", "Uygurlar'da", "Uygurlarda", C, "Uygurlar'da"),
    ("S12", "olduğu halde", "olduğu hâlde", C, "olduğu halde"),
    ("S12", "daîmidir", "daimidir / daimîdir", CG, "daîmidir"),
    ("S12", "Orta Çağda", "Orta Çağ'da", CG, "Orta Çağda"),
    ("S12", "Bilge Kağan Anıt Mezarlığında", "Bilge Kağan Anıt Mezarlığı'nda", C, "Bilge Kağan Anıt Mezarlığında"),
    ("S13", "vilâyetlerde", "vilayetlerde", C, "vilâyetlerde"),
    ("S13", "el Eş'arî'ye", "el-Eş'arî'ye", G, "el Eş'arî'ye"),
    ("S13", "tâlimatnâmesi", "talimatnamesi", C, "tâlimatnâmesi"),
    ("S13", "telâşa", "telaşa", C, "telâşa"),
    ("S13", "Gök Türk Devleti'ndeki", "Göktürk Devleti'ndeki", CG, "Gök Türk Devleti'ndeki"),
    ("S13", "Gök Türk Devleti'nin", "Göktürk Devleti'nin", CG, "Gök Türk Devleti'nin"),
    ("S13", "Sâsânî devleti", "Sâsânî Devleti", C, "Sâsânî devleti kurulduğu"),  # ChatGPT iki kez yazdı, tek madde
    ("S13", "içersinde", "içerisinde", CG, "içersinde"),
    ("S13", "âdil", "adil", C, "âdil bir yönetim"),
    ("S13", "müslüman muamelesi", "Müslüman muamelesi", C, "müslüman muamelesi"),
    ("S13", "müslümanlarla", "Müslümanlarla", C, "müslümanlarla"),
    ("S13", "Gayri müslimlerin", "Gayrimüslimlerin", CG, "Gayri müslimlerin"),
    ("S13", "müslümanlar aleyhindeki", "Müslümanlar aleyhindeki", C, "müslümanlar aleyhindeki"),
    ("S13", "Bizans imparatorluğuna", "Bizans İmparatorluğu'na", CG, "Bizans imparatorluğuna"),
    ("S13", "siyasî", "siyasi", C, "siyasî kargaşalar"),
    ("S13", "keyfi ve zulme varan", "keyfî ve zulme varan", C, "keyfi ve zulme varan"),
    ("S13", "Müslümanlara;", "Müslümanlara:", C, "Müslümanlara;"),
    ("S13", "Hükümetinizin", "Hükûmetinizin", C, "Hükümetinizin"),
    ("S14", "askeri merkezleri", "askerî merkezleri", C, "askeri merkezleri"),
    ("S15", "genel itibariyle", "genel itibarıyla", C, "genel itibariyle"),
    ("S16", "Topoğrafya", "Topografya", C, "Topoğrafya"),
    ("S16", "Bogoto", "Bogota", G, "Bogoto"),
    ("S16", "San Tiago", "Santiago", G, "San Tiago"),
    ("S17", "kuzey enlemi", "Kuzey enlemi", G, "kuzey enlemi"),
    ("S17", "doğu boylamının", "Doğu boylamının", G, "doğu boylamının"),
    ("S19", "Quebek", "Québec / Kebek", G, "Quebek"),
    ("S21", "1475'e", "1.475'e", C, "1475'e"),
    ("S21", "1475 aşırı hava olayıyla", "1.475 aşırı hava olayıyla", C, "1475 aşırı hava olayıyla"),
    ("S21", "1030", "1.030", C, "yıl 1030"),
    ("S21", "1024'tü", "1.024'tü", C, "1024'tü"),
    ("S21", "1000 (grafik ekseni)", "1.000", C, "1.200 1000 800"),
    ("S21", "M alatya'da", "Malatya'da", G, "M alatya'da"),
    ("S22", "Yer yüzeyinden yansıyan", "Yeryüzünden yansıyan", G, "Yer yüzeyinden yansıyan"),
    ("S23", "Kuzey yarım kürede", "Kuzey Yarım Küre'de", G, "Kuzey yarım kürede"),
    ("S24", "Ekvatoral bölgede", "ekvatoral bölgede", C, "Ekvatoral bölgede"),
    ("S24", "kuzey yarım kürede", "Kuzey Yarım Küre'de", G, "kuzey yarım kü- rede"),
    ("S24", "güney yarım kürede", "Güney Yarım Küre'de", G, "güney yarım kürede"),
    ("S25", "Güney kutup bölgesine", "Güney Kutup Bölgesi'ne", CG, "Güney kutup bölgesine"),
    ("S26", "azalacağı buna karşın", "azalacağı, buna karşın", C, "azalacağı buna karşın"),
    ("S26", "Nüfus Birimi'nin", "Nüfus Biriminin", C, "Nüfus Birimi'nin"),
    ("S30", "Kasım-2013", "Kasım 2013", C, "Kasım-2013"),
    ("S30", "Kasım-2014", "Kasım 2014", C, "Kasım-2014"),
    ("S30", "Aralık-2015", "Aralık 2015", C, "Aralık-2015"),
]

ATLANAN = [
    "S05 'MÕ 18.000'lerde' (G — kitapta zaten 'MÖ 18.000'lerde')",
    "S05 'besin kaynağı avcılık' (G — önerisi kitaptakiyle aynı)",
    "S06 'bitkiIerin' (G — kitapta 'bitkilerin'; görüntü okuma hatası)",
    "S09 'Düşman savaşçılann' (G — sayfa metninde yok)",
    "S11 'Doğu/Batı Roma Imparatorluğu' (G — kitapta 'İmparatorluğu')",
    "S15 'O'a doğru' (G — kitapta '0'a doğru')",
    "S18 '-03°28'01\" Doğu' → 'Batı' (G — sayfa metninde eksi işareti yok; öneri yazım değil, bilgi iddiası)",
    "S19 'coğrafı' (G — sayfa metninde yok)",
    "S25 '15°C''.' → '15°C'dir.' (G — sayfa metninde yok; kitapta '15 °C'tur')",
    "S26 '%5-%8' (G — önerisi kitaptakiyle aynı)",
    "S27 'ΕΚΟΝΟMİK' (G — kitapta 'EKONOMİK')",
    "S30 'm²lik' (G — önerisi kitaptakiyle aynı, kendi notu da 'doğru')",
    "S13 'Sâsânî devleti' ikinci satır (C — aynı yazım, tek maddeye katıldı)",
    "S21 grafik etiketleri '1024', '1030', '1475' (C — metindeki aynı sayılarla aynı iddia, tek maddeye katıldı)",
]


def n(s: str) -> str:
    return s.replace("’", "'").replace("‘", "'")


sayfalar = {x["kod"]: x for x in json.load(open(PAKET / "A_sayfa_listesi.json", encoding="utf-8"))}
pdfler = {k: pymupdf.open(PROJE / "veri" / f"{k}.pdf") for k in KITAP_AD}
glif = {kod: sayfa_glif_metni(pdfler[v["kitap"]][v["sayfa_no"] - 1]) for kod, v in sayfalar.items()}
metin = {}
for parca in open(PAKET / "A_30_sayfa_metin.txt", encoding="utf-8").read().split("===== ")[1:]:
    metin[parca[:3]] = " ".join(parca.split("=====", 1)[1].split())

anahtar, bulunamayan = [], []
for i, (kod, kitaptaki, oneri, kaynak, ara) in enumerate(M, 1):
    s, m = sayfalar[kod], metin[kod]
    j = n(m).find(n(ara))  # n() harf sayısını değiştirmez: dizinler asıl metinle aynı
    if j < 0:
        bulunamayan.append((kod, ara))
        gercek, yer = ara, "(sayfa metninde bulunamadı)"
    else:
        gercek = m[j:j + len(ara)]
        yer = ("…" if j > 90 else "") + m[max(0, j - 90):j + len(ara) + 90] + ("…" if j + len(ara) + 90 < len(m) else "")
    anahtar.append({
        "no": f"A{i:02d}", "sayfa": kod, "kitap": s["kitap"], "sayfa_no": s["sayfa_no"],
        "kitaptaki": kitaptaki, "onerilen": oneri, "kaynak": sorted(kaynak), "ara": gercek, "baglam": yer,
        "katman_farki": katman_farki(glif[kod], gercek),
    })

(CIKTI / "A_birlesik_anahtar.json").write_text(
    json.dumps({"maddeler": anahtar, "atlanan": ATLANAN}, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(M), "madde; ChatGPT yalnız", sum(k == C for *_, k, _ in M), "| Gemini yalnız", sum(k == G for *_, k, _ in M),
      "| ikisi", sum(k == CG for *_, k, _ in M), "| atlanan", len(ATLANAN))
print("metinde bulunamayan:", bulunamayan)
print("katman farkı:", [(x["no"], x["sayfa"], x["kitaptaki"], x["katman_farki"]) for x in anahtar if x["katman_farki"]])
