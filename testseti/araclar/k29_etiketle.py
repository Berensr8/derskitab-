"""K29 körlemesine yazım etiketleri: Biyoloji 9, Biyoloji 11, TDE 12 (180 tespit).

K29 kodu (PDF parçası, terim, alıntı v3) yazılmadan ÖNCE etiketlendi ve kilitlendi (Claude, kullanıcının
yetkisiyle, 2026-10-21). Etiket kuralları k23_etiketle.py ile aynı; "alinti_eski_yazim" edebî metin, şiir,
yazıt, konuşma aktarımı ve metnin sözlükçesindeki eski yazımları kapsar.
Çıktı: testseti/yazim_etiketler_k29.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")

G, B = "gercek", "belirsiz"
TERIM, ALINTI, PDF, DOGRU = "terim", "alinti_eski_yazim", "pdf_okuma", "dogru_kelime"
ETIKET = {
    # Biyoloji 9
    "B9-01": (PDF, "Gençliğe Hitabe: 'ı' özel glif"), "B9-02": (PDF, "Gençliğe Hitabe: 'ı' özel glif"),
    "B9-03": (ALINTI, "Gençliğe Hitabe: bîtap"), "B9-04": (TERIM, "mRNA"), "B9-05": (TERIM, "biyomolekül"),
    "B9-06": (TERIM, "İngilizce terimin okunuşu"), "B9-07": (DOGRU, "enfekte"), "B9-08": (TERIM, "Latince adın okunuşu"),
    "B9-09": (TERIM, "makromolekül"), "B9-10": (TERIM, "polimerik"), "B9-11": (TERIM, "monosakkarit"),
    "B9-12": (TERIM, "heksoz"), "B9-13": (TERIM, "sakkaroz"), "B9-14": (TERIM, "polisakkarit"),
    "B9-15": (TERIM, "polisakkarit"), "B9-16": (TERIM, "biyomolekül"), "B9-17": (TERIM, "koenzim"),
    "B9-18": (TERIM, "feedback (İngilizce karşılık)"), "B9-19": (TERIM, "aktivatör"), "B9-20": (TERIM, "koenzim"),
    "B9-21": (TERIM, "folik asit"), "B9-22": (TERIM, "karbohidrat"), "B9-23": (DOGRU, "asitlik"),
    "B9-24": (TERIM, "Latince ad"), "B9-25": (TERIM, "katabolik"), "B9-26": (TERIM, "oksidaz"),
    "B9-27": (TERIM, "benzokinon"), "B9-28": (TERIM, "por"), "B9-29": (TERIM, "karbohidrat"),
    "B9-30": (TERIM, "karoten"), "B9-31": (TERIM, "fosfolipit"), "B9-32": (DOGRU, "asitlik"),
    "B9-33": (TERIM, "Latince adın okunuşu"), "B9-34": (TERIM, "Latince adın okunuşu"),
    "B9-35": (TERIM, "Latince adın okunuşu"), "B9-36": (TERIM, "Latince ad"), "B9-37": (TERIM, "kromozomal"),
    "B9-38": (TERIM, "biyoteknolojik"), "B9-39": (TERIM, "Latince ad"), "B9-40": (TERIM, "Latince ad"),
    "B9-41": (TERIM, "probiyotik"), "B9-42": (TERIM, "siyanobakteri"), "B9-43": (TERIM, "knidosit"),
    "B9-44": (TERIM, "Latince adın okunuşu"), "B9-45": (TERIM, "Latince ad"), "B9-46": (TERIM, "Latince adın okunuşu"),
    "B9-47": (TERIM, "biyoyakıt"), "B9-48": (TERIM, "Latince adın okunuşu"), "B9-49": (TERIM, "glikan (sözlükte)"),
    "B9-50": (DOGRU, "sentezliyor"),
    # Biyoloji 11
    "B11-01": (PDF, "Gençliğe Hitabe: 'ı' özel glif"), "B11-02": (ALINTI, "Gençliğe Hitabe: elîm"),
    "B11-03": (G, "sorumluklar → sorumluluklar"), "B11-04": (TERIM, "Latince adın okunuşu"),
    "B11-05": (TERIM, "Latince ad"), "B11-06": (TERIM, "Latince adın okunuşu"), "B11-07": (TERIM, "Latince adın okunuşu"),
    "B11-08": (TERIM, "Latince adın okunuşu"), "B11-09": (TERIM, "Latince ad"), "B11-10": (TERIM, "Latince ad"),
    "B11-11": (TERIM, "Latince adın okunuşu"), "B11-12": (TERIM, "agar"), "B11-13": (TERIM, "agar"),
    "B11-14": (TERIM, "grid"), "B11-15": (TERIM, "impuls"), "B11-16": (TERIM, "ultrasonik"),
    "B11-17": (TERIM, "Latince adın okunuşu"), "B11-18": (TERIM, "Latince ad"), "B11-19": (TERIM, "Latince adın okunuşu"),
    "B11-20": (TERIM, "pons"), "B11-21": (TERIM, "filament"), "B11-22": (TERIM, "filament"), "B11-23": (TERIM, "mRNA"),
    "B11-24": (TERIM, "rinit"), "B11-25": (TERIM, "paramesyum"), "B11-26": (TERIM, "ürik asit"),
    "B11-27": (G, "nokta sonrası boşluk yok"), "B11-28": (TERIM, "lob"), "B11-29": (TERIM, "gliserol"),
    "B11-30": (B, "'noroepinefrin' — yaygın yazım 'norepinefrin', yazım hatası olabilir"),
    "B11-31": (TERIM, "fraktal"), "B11-32": (TERIM, "sitoplazmik"), "B11-33": (TERIM, "bronşiol"),
    "B11-34": (TERIM, "pons"), "B11-35": (G, "fazldır → fazladır"), "B11-36": (TERIM, "timpani (çalgı)"),
    "B11-37": (DOGRU, "anakart"), "B11-38": (PDF, "derece işareti 'o' okunmuş"), "B11-39": (TERIM, "hipertermi"),
    "B11-40": (TERIM, "mmHg"), "B11-41": (TERIM, "hipotonik"), "B11-42": (G, "antogonist → antagonist"),
    "B11-43": (TERIM, "ovaryum (sözlükte)"), "B11-44": (TERIM, "deaminasyon (sözlükte)"),
    "B11-45": (TERIM, "endositoz (sözlükte)"), "B11-46": (TERIM, "miyoblast (sözlükte)"),
    "B11-47": (TERIM, "nörofibril (sözlükte)"), "B11-48": (TERIM, "peristaltik (sözlükte)"),
    "B11-49": (TERIM, "mikotoksin (sözlükte)"), "B11-50": (G, "klavuzu → kılavuzu (kaynakçada)"),
    # Türk Dili ve Edebiyatı 12
    "T12-01": (PDF, "Gençlik Marşı: 'ı' özel glif"), "T12-02": (PDF, "İstiklal Marşı: 'ı' özel glif"),
    "T12-03": (PDF, "İstiklal Marşı: 'ı' özel glif"), "T12-04": (ALINTI, "İstiklal Marşı: nâmahrem"),
    "T12-05": (ALINTI, "İstiklal Marşı: vecd"), "T12-06": (ALINTI, "İstiklal Marşı: hürriyyet"),
    "T12-07": (ALINTI, "metinden alıntı: yaştanberi"), "T12-08": (PDF, "satır sonunda bölünmüş (da-ha)"),
    "T12-09": (DOGRU, "büyüklü küçüklü"), "T12-10": (DOGRU, "büyüklü küçüklü"),
    "T12-11": (ALINTI, "deneme metninde bilerek yabancı kelime"), "T12-12": (ALINTI, "okuma metni: yükleyim"),
    "T12-13": (ALINTI, "okuma metni, konuşma dili: burda"), "T12-14": (ALINTI, "hikâye: avaze"),
    "T12-15": (ALINTI, "eski imla: duyamıyacağı"), "T12-16": (ALINTI, "mânalı"), "T12-17": (ALINTI, "hikâye: dumanımsı"),
    "T12-18": (ALINTI, "hikâye: çığırttıran"), "T12-19": (ALINTI, "hikâye: yorulunmuştur"),
    "T12-20": (DOGRU, "göçmenlerle"), "T12-21": (ALINTI, "diyalog: içerde"), "T12-22": (DOGRU, "sözgelimi"),
    "T12-23": (ALINTI, "hikâye: yazarın yazımı 'Herşey'"), "T12-24": (ALINTI, "hikâye, konuşma: orda"),
    "T12-25": (TERIM, "minimalize"), "T12-26": (ALINTI, "hikâye: yazarın yazımı 'boşlukda'"),
    "T12-27": (ALINTI, "hikâye: istimbot"), "T12-28": (ALINTI, "İngilizce alıntı"),
    "T12-29": (PDF, "satır sonunda bölünmüş (Ta-rihi)"), "T12-30": (ALINTI, "şiir: küçük harfli ad"),
    "T12-31": (ALINTI, "şiir: pazu"), "T12-32": (G, "söyleyebillirsiniz → söyleyebilirsiniz (kitabın sorusu)"),
    "T12-33": (ALINTI, "âhenk"), "T12-34": (ALINTI, "metnin sözlükçesi: kitâbe"), "T12-35": (ALINTI, "şiir"),
    "T12-36": (DOGRU, "kimlere"), "T12-37": (ALINTI, "şiir: isteyorsan"), "T12-38": (ALINTI, "şiir: süd"),
    "T12-39": (ALINTI, "roman: lâfazan"), "T12-40": (ALINTI, "roman: lâvanta"), "T12-41": (ALINTI, "roman: üşümeğe"),
    "T12-42": (ALINTI, "roman: sebu"), "T12-43": (ALINTI, "hikâye: göğermek"),
    "T12-44": (ALINTI, "metindeki kelime soruluyor"), "T12-45": (PDF, "satır sonunda bölünmüş"),
    "T12-46": (ALINTI, "hikâye: herbir"), "T12-47": (ALINTI, "hikâye: üstüste"), "T12-48": (ALINTI, "hikâye: külrengi"),
    "T12-49": (DOGRU, "nelerin"), "T12-50": (DOGRU, "evecen (sözlükçe)"), "T12-51": (ALINTI, "hikâye: işi mişi"),
    "T12-52": (ALINTI, "hikâye: süd"), "T12-53": (ALINTI, "çeviri metin: döğülecek"), "T12-54": (ALINTI, "oyun: İngilizce replik"),
    "T12-55": (ALINTI, "metnin sözlükçesi: İngilizce"), "T12-56": (DOGRU, "ikileme: için için"),
    "T12-57": (ALINTI, "deneme: söyleyi söyleyiverirsiniz"), "T12-58": (ALINTI, "deneme: yermeğe"),
    "T12-59": (ALINTI, "deneme: ettirmeğe"), "T12-60": (DOGRU, "insanoğlu"), "T12-61": (ALINTI, "vaitkâr"),
    "T12-62": (ALINTI, "deneme: birarada"), "T12-63": (ALINTI, "eski imla: yaşıyacak"), "T12-64": (ALINTI, "başucu"),
    "T12-65": (ALINTI, "eski imla: arıyacaksınız"), "T12-66": (ALINTI, "metnin sözlükçesi: elîm"),
    "T12-67": (ALINTI, "dâima"), "T12-68": (ALINTI, "mevkii"), "T12-69": (ALINTI, "şâhidliği"), "T12-70": (ALINTI, "mâzi"),
    "T12-71": (ALINTI, "vücude"), "T12-72": (ALINTI, "eski imla: olmıyan"), "T12-73": (DOGRU, "hezarfen (sözlükçe)"),
    "T12-74": (ALINTI, "Orhun yazıtı"), "T12-75": (ALINTI, "Orhun yazıtı"), "T12-76": (ALINTI, "Orhun yazıtı"),
    "T12-77": (ALINTI, "Orhun yazıtı"), "T12-78": (ALINTI, "nutuk: zaptetmek"), "T12-79": (ALINTI, "şiir: üzre"),
    "T12-80": (B, "'sinikallikle' — çeviri metinde; dizgi hatası mı özgün mü belirsiz"),
}

liste = json.loads((PROJE / "testseti" / "yazim_etiket_listesi_k29.json").read_text(encoding="utf-8"))
assert {x["id"] for x in liste} == set(ETIKET), "etiketsiz ya da fazladan madde var"
for x in liste:
    tur, aciklama = ETIKET[x["id"]]
    x["etiket"] = tur if tur in (G, B) else "sahte"
    x["sebep"] = None if tur in (G, B) else tur
    x["not"] = aciklama
(PROJE / "testseti" / "yazim_etiketler_k29.json").write_text(json.dumps(liste, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
for kitap in ("biyoloji9", "biyoloji11", "turkdili12"):
    e = [x for x in liste if x["kitap"] == kitap]
    print(kitap, Counter(x["etiket"] for x in e), Counter(x["sebep"] for x in e if x["sebep"]).most_common())
