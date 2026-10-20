"""K23 precision etiketleri (Claude, kullanıcının yetkisiyle, 2026-10-20).

gercek  : kitabın kendi metninde düzeltilmesi gereken yazım/noktalama hatası
sahte   : doğru yazılmış (sebep kategorisiyle)
belirsiz: tasarım tercihi ya da TDK'de tartışmalı — precision hesabına katılmaz, ayrıca raporlanır
Çıktı: testseti/yazim_etiketler.json
"""
import json
import sys
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")

G, B = "gercek", "belirsiz"
# Sahte sebepleri
TERIM, OZEL, ALINTI, PDF, DOGRU, HARITA, SAYI = ("terim", "ozel_isim", "alinti_eski_yazim", "pdf_okuma",
                                               "dogru_kelime", "harita_etiketi", "sayi_parcalama")
ETIKET = {
    # Sosyal Bilgiler 6 (tüm tespitler)
    "ES01": (G, "katılacağınıizı"), "ES02": (G, "noktadan sonra boşluk yok"), "ES03": (G, "kişisel"),
    "ES04": (G, "gelişimimiz"), "ES05": (G, "noktadan sonra boşluk yok"),
    "ES06": (B, "(…) öncesi boşluk: tasarım tercihi"), "ES07": (B, "'nesilden nesile' deyim olarak da kullanılıyor"),
    "ES08": (TERIM, "Eski Türkçe kavram (tüzlük)"), "ES09": (B, "alıntı: 'hoşgörülükte'"),
    "ES10": (B, "(…) öncesi boşluk"), "ES11": (B, "(…) öncesi boşluk"), "ES12": (B, "(…) öncesi boşluk"),
    "ES13": (DOGRU, "omuz omuza"), "ES14": (DOGRU, "omuz omuza"), "ES15": (G, "listeyi"),
    "ES16": (OZEL, "para birimi adı"), "ES17": (PDF, "harf aralıklı harita etiketi parçası"),
    "ES18": (G, "sürdürülebilirliğe"), "ES19": (DOGRU, "ithafen"), "ES20": (G, "noktadan sonra boşluk yok"),
    "ES21": (PDF, "satırda bölünmüş kelime parçası"), "ES22": (DOGRU, "icraatlar"),
    "ES23": (G, "kaynakçada virgülden sonra boşluk yok"), "ES24": (G, "noktadan sonra boşluk yok"),
    "ES25": (G, "noktadan sonra boşluk yok"), "ES26": (G, "görülen"), "ES27": (HARITA, "şehir adları listesi"),
    "ES28": (B, "'oğula' / 'oğla' tartışmalı"), "ES29": (G, "jandarma"), "ES30": (TERIM, "askerî unvan"),
    "ES31": (G, "kullanmaları"), "ES32": (TERIM, "Eski Türkçe (oguş)"), "ES33": (TERIM, "Eski Türkçe (tüzlük)"),
    "ES34": (TERIM, "Eski Türkçe (yargu)"), "ES35": (DOGRU, "kadarıyla"), "ES36": (G, "değiş tokuş ayrı yazılır"),
    "ES37": (DOGRU, "karekod"), "ES38": (TERIM, "mevali"), "ES39": (TERIM, "mevali"), "ES40": (TERIM, "mevali"),
    "ES41": (TERIM, "suffe"), "ES42": (G, "kutusundaki"), "ES43": (ALINTI, "şapkalı eski yazım"),
    "ES44": (TERIM, "dâru'l-imâre"), "ES45": (ALINTI, "alıntıda 'katib'"), "ES46": (DOGRU, "icraatlardan"),
    "ES47": (TERIM, "küttâb"), "ES48": (DOGRU, "icraatlarından"), "ES49": (ALINTI, "divân"),
    "ES50": (B, "TDK 'tezhip'; alıntı olabilir"), "ES51": (B, "(…) öncesi boşluk"), "ES52": (ALINTI, "ihdâs"),
    "ES53": (TERIM, "kâdı'l-kudâtlık"), "ES54": (TERIM, "başkadı"), "ES55": (TERIM, "başkadılık"),
    "ES56": (DOGRU, "resfebe"), "ES57": (DOGRU, "resfebenin"), "ES58": (B, "(...) öncesi boşluk"),
    "ES59": (DOGRU, "sembolize"), "ES60": (ALINTI, "mefkûre"), "ES61": (TERIM, "ribat"),
    "ES62": (HARITA, "Pei-ting"), "ES63": (B, "(...) öncesi boşluk"), "ES64": (TERIM, "ribat"),
    "ES65": (G, "önemlilerinden"), "ES66": (DOGRU, "ithafen"), "ES67": (TERIM, "ribat"),
    "ES68": (G, "kullanmışlardır"), "ES69": (G, "planında"), "ES70": (G, "planında"),
    "ES71": (DOGRU, "şapka tercihi (istilâ)"), "ES72": (DOGRU, "tıbba"), "ES73": (TERIM, "suffe"),
    "ES74": (DOGRU, "hadisişerif"), "ES75": (B, "'dü şünme': dizgi mi PDF mi belirsiz"),
    "ES76": (DOGRU, "nanometre"), "ES77": (DOGRU, "ashabıkiram"), "ES78": (TERIM, "kudâtlık"),
    # Biyoloji 10 (sabit tohumlu 50 tespit)
    "EB01": (ALINTI, "İstiklal Marşı: vecd"), "EB02": (ALINTI, "İstiklal Marşı: cerîha"), "EB03": (DOGRU, "arşa"),
    "EB04": (ALINTI, "İstiklal Marşı: va'd"), "EB05": (PDF, "kıymetli: harf düşmüş parça"),
    "EB06": (ALINTI, "Gençliğe Hitabe: hâricî"), "EB07": (TERIM, "nükleotit"), "EB08": (TERIM, "monofosfat"),
    "EB09": (TERIM, "karoten"), "EB10": (TERIM, "sükroz"), "EB11": (DOGRU, "soğurulan"),
    "EB12": (G, "arkadaşlarınızla"), "EB13": (DOGRU, "şöyledir"), "EB14": (TERIM, "arke"),
    "EB15": (DOGRU, "deneyimleyen"), "EB16": (TERIM, "nötral yağ"), "EB17": (TERIM, "nötralize"),
    "EB18": (TERIM, "bilirubin"), "EB19": (TERIM, "trigliserit"), "EB20": (TERIM, "alveol"),
    "EB21": (TERIM, "nikotinamid"), "EB22": (TERIM, "metanojenik"), "EB23": (DOGRU, "grid"),
    "EB24": (DOGRU, "enzimatik"), "EB25": (TERIM, "ülseratif"), "EB26": (DOGRU, "anabolik"),
    "EB27": (G, "noktadan sonra boşluk yok"), "EB28": (DOGRU, "gluten"), "EB29": (TERIM, "Latince tür adı"),
    "EB30": (TERIM, "Anadolu gelengisi"), "EB31": (TERIM, "okunuş rehberi"), "EB32": (TERIM, "hif"),
    "EB33": (DOGRU, "parazitik"), "EB34": (G, "soru işaretinden sonra boşluk yok"),
    "EB35": (SAYI, "1960'larda parçası"), "EB36": (OZEL, "İtai itai hastalığı"), "EB37": (OZEL, "İtai itai hastalığı"),
    "EB38": (DOGRU, "ppm'ye"), "EB39": (TERIM, "denitrifikasyon"), "EB40": (TERIM, "nitrifikasyon"),
    "EB41": (DOGRU, "nitrite (nitrit+e)"), "EB42": (DOGRU, "salım"), "EB43": (TERIM, "maar"),
    "EB44": (TERIM, "kloroflorokarbon"), "EB45": (DOGRU, "nelerin"), "EB46": (TERIM, "takson"),
    "EB47": (TERIM, "permakültür"), "EB48": (DOGRU, "mikroplastik"), "EB49": (SAYI, "1960'lardan parçası"),
    "EB50": (TERIM, "mikroflora"),
}

liste = json.loads((PROJE / "testseti" / "yazim_etiket_listesi.json").read_text(encoding="utf-8"))
assert {x["id"] for x in liste} == set(ETIKET), "etiketsiz ya da fazladan madde var"
for x in liste:
    tur, aciklama = ETIKET[x["id"]]
    x["etiket"] = tur if tur in (G, B) else "sahte"
    x["sebep"] = None if tur in (G, B) else tur
    x["not"] = aciklama
(PROJE / "testseti" / "yazim_etiketler.json").write_text(json.dumps(liste, ensure_ascii=False, indent=1),
                                                         encoding="utf-8")
from collections import Counter  # noqa: E402
for kitap in ("kitap", "biyoloji10"):
    e = [x for x in liste if x["kitap"] == kitap]
    print(kitap, Counter(x["etiket"] for x in e), Counter(x["sebep"] for x in e if x["sebep"]).most_common())
