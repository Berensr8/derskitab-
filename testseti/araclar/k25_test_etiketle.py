"""K25 precision TEST etiketleri: Matematik 11 ve TDE 9'dan 40'ar tespit.

Yazım hakemi (dil modeli) HİÇ çalıştırılmadan etiketlendi ve commit edildi (Claude, kullanıcının
yetkisiyle, 2026-10-20). Etiket kuralları k23_etiketle.py ile aynı.
Çıktı: testseti/yazim_etiketler_test.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")

G, B = "gercek", "belirsiz"
TERIM, OZEL, ALINTI, PDF, DOGRU = "terim", "ozel_isim", "alinti_eski_yazim", "pdf_okuma", "dogru_kelime"
ETIKET = {
    # Matematik 11
    "TM01": (PDF, "Gençliğe Hitabe: harf düşmüş parça"), "TM02": (ALINTI, "elîm"), "TM03": (ALINTI, "bîtap"),
    "TM04": (DOGRU, "modellemiştir"), "TM05": (DOGRU, "tablolama"), "TM06": (DOGRU, "siber"),
    "TM07": (DOGRU, "kadarının"), "TM08": (DOGRU, "nerelerden"), "TM09": (G, "virgülden sonra boşluk yok"),
    "TM10": (PDF, "derece işareti 'c' okunmuş"), "TM11": (PDF, "derece işareti 'c' okunmuş"),
    "TM12": (B, "'draftın' — teknik terim mi yazım hatası mı belirsiz"), "TM13": (PDF, "dikdörtgen bölünmüş"),
    "TM14": (G, "paralelkenarın"), "TM15": (B, "'onbeşgen' / 'on beşgen' tartışmalı"),
    "TM16": (PDF, "çizildiğinde bölünmüş"), "TM17": (G, "sekizgen"), "TM18": (PDF, "formül içinde parça"),
    "TM19": (B, "'nesilden nesile' deyim olarak da kullanılıyor"), "TM20": (DOGRU, "ondalık"),
    "TM21": (TERIM, "newton (birim)"), "TM22": (G, "olacağını"), "TM23": (PDF, "'fonksiyon de|ğeri' bloklara bölünmüş"),
    "TM24": (G, "fonksiyon"), "TM25": (PDF, "satır sonu tiresi kaybolmuş (bağımlı-bağımsız)"),
    "TM26": (TERIM, "watt"), "TM27": (TERIM, "watt"), "TM28": (PDF, "'fonksiyon de|ğeri' bloklara bölünmüş"),
    "TM29": (B, "'inmektedir.h' — formül değişkeni, boşluk PDF'te olabilir"), "TM30": (TERIM, "watt"),
    "TM31": (TERIM, "watt"), "TM32": (TERIM, "watt"), "TM33": (G, "virgülden sonra boşluk yok"),
    "TM34": (DOGRU, "bloğunun"), "TM35": (G, "temsillerini"), "TM36": (G, "fonksiyonlar"),
    "TM37": (TERIM, "kWh"), "TM38": (B, "'işeklinde' — formül işareti 'i' okunmuş olabilir"),
    "TM39": (DOGRU, "modellemiştir"), "TM40": (DOGRU, "paralimpik"),
    # Türk Dili ve Edebiyatı 9
    "TT01": (ALINTI, "Mehmet Akif: te'sis"), "TT02": (ALINTI, "iclâl"), "TT03": (ALINTI, "şehîd"),
    "TT04": (ALINTI, "gülzâr (açıklanan kelime)"), "TT05": (ALINTI, "Eski Anadolu Türkçesi beyit"),
    "TT06": (ALINTI, "eski imla: söylemiyecek"), "TT07": (DOGRU, "kadarıyla"), "TT08": (DOGRU, "sohbetlik"),
    "TT09": (ALINTI, "şâir"), "TT10": (ALINTI, "mahlul"), "TT11": (DOGRU, "avcundan"), "TT12": (ALINTI, "mel'un"),
    "TT13": (DOGRU, "karışıksız"), "TT14": (DOGRU, "bulanıksız"), "TT15": (ALINTI, "eski imla: tamamıyle"),
    "TT16": (ALINTI, "meşâhir"), "TT17": (ALINTI, "vâr"), "TT18": (ALINTI, "vecd"), "TT19": (ALINTI, "nidâ"),
    "TT20": (ALINTI, "diyâr"), "TT21": (ALINTI, "konuşma dili: âbi"), "TT22": (DOGRU, "kadarını"),
    "TT23": (ALINTI, "Yunus Emre: derdüme"), "TT24": (ALINTI, "mâhî"), "TT25": (ALINTI, "Azerbaycan Türkçesi"),
    "TT26": (ALINTI, "Azerbaycan Türkçesi"), "TT27": (TERIM, "kafiye şeması harfleri"), "TT28": (ALINTI, "türkü"),
    "TT29": (ALINTI, "destânî"), "TT30": (ALINTI, "konuşma dili: nerden"), "TT31": (ALINTI, "hakikî"),
    "TT32": (ALINTI, "ahbâb"), "TT33": (ALINTI, "rezîlâne"), "TT34": (ALINTI, "mâzî"), "TT35": (ALINTI, "dehâ"),
    "TT36": (ALINTI, "âguş"), "TT37": (ALINTI, "hâlis"), "TT38": (ALINTI, "lisân"),
    "TT39": (B, "'gramafon' — sözlü anlatı aktarımı olabilir"), "TT40": (DOGRU, "kıpır kıpır"),
}

liste = json.loads((PROJE / "testseti" / "yazim_etiket_listesi_test.json").read_text(encoding="utf-8"))
assert {x["id"] for x in liste} == set(ETIKET), "etiketsiz ya da fazladan madde var"
for x in liste:
    tur, aciklama = ETIKET[x["id"]]
    x["etiket"] = tur if tur in (G, B) else "sahte"
    x["sebep"] = None if tur in (G, B) else tur
    x["not"] = aciklama
(PROJE / "testseti" / "yazim_etiketler_test.json").write_text(json.dumps(liste, ensure_ascii=False, indent=1),
                                                              encoding="utf-8")
for kitap in ("matematik11", "turkdili9"):
    e = [x for x in liste if x["kitap"] == kitap]
    print(kitap, Counter(x["etiket"] for x in e), Counter(x["sebep"] for x in e if x["sebep"]).most_common())
