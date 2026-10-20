"""K20 taslak çelişki setini oluşturur: doğrular, hedef paragrafları seçer, geliştirme/test ayırır."""
import json
import re
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"D:\derskitabı")
from derskitabi.kayit import bloklari_yukle  # noqa: E402
from derskitabi.kriterler.tutarlilik import _ETKINLIK, _YONERGE, ollama_gomucu  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent))
from k20_soru import etkinlik_bloklari  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# (id, tür, yöntem, kaynaklar [(sayfa, blok, cümle parçası)], hedef)
#   tekrar_boz : hedef = (sayfa, blok, eski, yeni)  -> blokta eski metin yeni ile değiştirilir
#   yeniden_yaz: hedef = yeni cümle                  -> uygun bir paragrafın sonuna eklenir
SET = {
 "kitap": [
  ("S01", "tarih", "tekrar_boz", [(155, 1, "1071 yılında Doğu Roma"), (164, 5, "26 Ağustos 1071"), (172, 23, "1071’de gerçekleşen Malazgirt")],
   (179, 7, "Böylece 1071 yılında iki ordu", "Böylece 1074 yılında iki ordu")),
  ("S02", "tarih", "tekrar_boz", [(154, 59, "Pasinler Savaşı'nda (1048)"), (172, 30, "1048’de gerçekleşen Pasinler"), (179, 2, "1048’de Pasinler Ovası")],
   (162, 7, "1048’de Selçuklular ile", "1058’de Selçuklular ile")),
  ("S03", "sayi", "tekrar_boz", [(42, 25, "2 milyon 682 bin 673"), (83, 8, "2 milyon 682 bin 673"), (42, 24, "yaklaşık 2,7 milyon")],
   (84, 1, "2 milyon 682 bin 673 kişi", "3 milyon 482 bin 673 kişi")),
  ("S04", "sayi", "tekrar_boz", [(45, 2, "yaklaşık yüzde 35'i")],
   (50, 15, "yaklaşık yüzde 35'i sofralara ulaşmadan", "yaklaşık yüzde 15'i sofralara ulaşmadan")),
  ("S05", "sayi", "tekrar_boz", [(71, 64, "yerel saat farkı 4 dakika"), (71, 65, "x 4 dakika")],
   (69, 15, "yerel saat farkı 4 dakikadır", "yerel saat farkı 15 dakikadır")),
  ("S06", "sayi", "tekrar_boz", [(45, 2, "12 milyon ekmek")],
   (50, 15, "yaklaşık 12 milyon ekmek", "yaklaşık 3 milyon ekmek")),
  ("S07", "isim", "tekrar_boz", [(149, 1, "Kaşgarlı Mahmud tarafından yazılan Divanü"), (149, 4, "Kaşgarlı Mahmud tarafından yazılan Divanü")],
   (152, 6, "Kaşgarlı Mahmud’un Divanü Lügati't-Türk adlı", "Yusuf Has Hâcib’in Divanü Lügati't-Türk adlı")),
  ("S08", "sozel", "tekrar_boz", [(149, 6, "Türkçe konuşulmaya devam etmiştir"), (149, 6, "halk arasında Türkçe konuşulmaya")],
   (159, 7, "Türkçe konuşulmaya devam edilmiş ancak Arapça ve Farsça kelimeler dilimize girmeye başlamıştır.",
             "Bu dönemde Türkçe konuşulmaz olmuş, yerini tamamen Arapça ve Farsça almıştır.")),
  ("S09", "tarih", "yeniden_yaz", [(130, 21, "622 yılında Mekke'den Medine'ye"), (134, 11, "hicret tarihi olan 622")],
   (29, 2, "Hz. Muhammed'in (sav) Mekke'den Medine'ye hicreti 632 yılında gerçekleşmiştir.")),
  ("S10", "tarih", "yeniden_yaz", [(95, 8, "Sovyet Rusya dağılmış (1991)")],
   "1985 yılında Sovyetler Birliği'nin yıkılmasıyla Orta Asya'daki Türk devletleri bağımsızlıklarını kazandı."),
  ("S11", "tarih", "yeniden_yaz", [(24, 4, "2021 yılından itibaren")],
   "Kültür ve Turizm Bakanlığının düzenlediği Kültür Yolu Festivalleri ilk kez 2015 yılında yapılmaya başlanmıştır."),
  ("S12", "tarih", "yeniden_yaz", [(98, 7, "Barış Manço, 1991'de devlet sanatçısı")],
   "Şarkılarıyla kültür elçiliği yapan Barış Manço, 1985 yılında devlet sanatçısı unvanını almıştır."),
  ("S13", "sayi", "yeniden_yaz", [(40, 8, "6,6 milyon kişinin yaşadığı")],
   "Fas'taki büyük depremden etkilenen bölgelerde yaklaşık 1,5 milyon kişi yaşamaktadır."),
  ("S14", "sayi", "yeniden_yaz", [(41, 12, "yaklaşık 7 milyon kişinin hayatını")],
   "Dünyada hava kirliliği nedeniyle her yıl yaklaşık 700 bin kişi hayatını kaybetmektedir."),
  ("S15", "sayi", "yeniden_yaz", [(90, 14, "%75'i Türkiye'dedir")],
   (85, 81, "Dünyadaki fındık dikim alanlarının yaklaşık üçte biri ülkemizde bulunmaktadır.")),
  ("S16", "sayi", "yeniden_yaz", [(82, 81, "%18,3'ünün ikamet ettiği İstanbul")],
   "Türkiye nüfusunun yaklaşık üçte biri İstanbul'da yaşamaktadır."),
  ("S17", "isim", "yeniden_yaz", [(68, 16, "Londra yakınındaki Greenwhich")],
   "Başlangıç meridyeni, Fransa'nın başkenti Paris'teki gözlemevinden geçen çizgi olarak kabul edilir."),
  ("S18", "isim", "yeniden_yaz", [(62, 6, "Romanya'nın başkenti Bükreş")],
   "Karadeniz kıyısındaki komşumuz Romanya'nın başkenti Köstence şehridir."),
  ("S19", "isim", "yeniden_yaz", [(61, 10, "Rusya Federasyonu'nun başkenti Moskova")],
   "Kuzeydoğu komşularımızdan Rusya Federasyonu'nun başkenti St. Petersburg'dur."),
  ("S20", "en_ilk", "yeniden_yaz", [(149, 4, "Türkçenin bilinen ilk sözlüğü")],
   "Türkçenin bilinen ilk sözlüğü, Yusuf Has Hâcib'in yazdığı Kutadgu Bilig'dir."),
  ("S21", "en_ilk", "yeniden_yaz", [(146, 8, "en çok tercih edilen hayvan at idi")],
   "Orta Asya Türklerinin hayvan yetiştiriciliğinde en çok tercih ettiği hayvan koyundu."),
  ("S22", "en_ilk", "yeniden_yaz", [(82, 81, "5 milyon 910 bin 320 kişi ile Ankara")],
   "Nüfusu en kalabalık ikinci ilimiz İzmir'dir."),
  ("S23", "sozel", "yeniden_yaz", [(149, 1, "yazılı edebî eserler yaygınlaşmıştır")],
   (146, 11, "İslamiyet'in kabulünden sonraki dönemde Türkler arasında yazılı edebiyat geriledi ve sözlü gelenek ön plana çıktı.")),
  ("S24", "sozel", "yeniden_yaz", [(155, 1, "Selçuklular tarafından kazanılmıştır")],
   "Malazgirt'te Doğu Roma ordusunun galip gelmesi, Selçukluların Anadolu'ya ilerleyişini uzun süre durdurdu."),
  ("S25", "sozel", "yeniden_yaz", [(92, 196, "Orta Asya'daki Türk boylarına dayanır")],
   "Türk dünyasının kökeni, Balkanlarda yaşayan eski topluluklara uzanmaktadır."),
 ],
 "biyoloji10": [
  ("B01", "sayi", "tekrar_boz", [(61, 6, "iki kez gerçekleşir")],
   (63, 35, "iki kez Krebs döngüsü gerçekleşir", "bir kez Krebs döngüsü gerçekleşir")),
  ("B02", "sayi", "tekrar_boz", [(60, 6, "2 adet piruvat"), (60, 4, "2 molekül piruvata")],
   (71, 3, "2 ATP ve 2 piruvat", "2 ATP ve 4 piruvat")),
  ("B03", "sayi", "tekrar_boz", [(47, 4, "dört bölmeli mide"), (41, 28, "dört bölmeden"), (189, 36, "dört bölümlü midenin")],
   (47, 11, "işkembe, börkenek, kırkbayır ve şirden olmak üzere dört bölümden", "işkembe, börkenek ve şirden olmak üzere üç bölümden")),
  ("B04", "sozel", "tekrar_boz", [(119, 10, "aşamalı olarak değişmesine süksesyon"), (119, 11, "zamanla aşamalı olarak")],
   (185, 16, "zaman içinde aşamalı olarak değişmesi sürecidir", "kısa sürede ve aniden, tek seferde değişmesi sürecidir")),
  ("B05", "isim", "tekrar_boz", [(98, 4, "Ekoloji, bu karmaşık etkileşimleri")],
   (101, 3, "bilim dalına ekoloji adı verilir", "bilim dalına etoloji adı verilir")),
  ("B06", "sozel", "tekrar_boz", [(51, 19, "Kalın bağırsakta sindirim gerçekleşmez")],
   (55, 21, "Kalın bağırsakta minerallerin (elektrolitlerin) ve suyun emilimi gerçekleşir.",
             "Kalın bağırsakta proteinlerin kimyasal sindirimi tamamlanır ve suyun emilimi gerçekleşir.")),
  ("B07", "sozel", "tekrar_boz", [(27, 27, "Işığın kullanılmadığı tepkimeler Calvin döngüsü")],
   (35, 9, "fotosentezin ışığın kullanılmadığı tepkimelerinde döngüsel", "fotosentezin ışığın kullanıldığı tepkimelerinde döngüsel")),
  ("B08", "sozel", "tekrar_boz", [(45, 19, "Heterotrof canlılar ise kendi besinlerini üretme yeteneğine sahip olmadığı")],
   (188, 26, "Kendi organik besinini üretemediği için bu besinleri dışarıdan almak zorunda olan canlılar.",
              "Kendi organik besinini ışık enerjisini kullanarak üretebilen canlılar.")),
  ("B09", "isim", "tekrar_boz", [(188, 25, "habitat: Bir canlı türünü")],
   (114, 6, "doğal yaşam ortamı habitat olarak adlandırılır", "doğal yaşam ortamı popülasyon olarak adlandırılır")),
  ("B10", "sozel", "yeniden_yaz", [(60, 4, "hücrenin sitoplazmasında 2 molekül")],
   "Ökaryot hücrelerde glikoliz tepkimeleri mitokondrinin iç zarında gerçekleşir."),
  ("B11", "tarih", "yeniden_yaz", [(30, 2, "1883 yılında Theodore Engelmann")],
   "Engelmann, ışığın dalga boyunun fotosenteze etkisini gösteren deneyini 1923 yılında yapmıştır."),
  ("B12", "tarih", "yeniden_yaz", [(35, 7, "Robert Hill (Robert Hill), 1937")],
   "Robert Hill'in fotosentezin ışığa bağlı tepkimeleri üzerindeki çalışmaları 1957 yılına aittir."),
  ("B13", "tarih", "yeniden_yaz", [(39, 12, "28 Nisan 1993 tarihinde")],
   "Ümraniye Hekimbaşı çöplüğündeki metan gazı patlaması 2003 yılında yaşanmıştır."),
  ("B14", "tarih", "yeniden_yaz", [(142, 7, "1998 yılında (260 km2lik kısmı) tabiat anıtı")],
   "Meke Krater Gölü, 2008 yılında tabiat anıtı olarak koruma altına alınmıştır."),
  ("B15", "sayi", "yeniden_yaz", [(142, 6, "yaklaşık 5 milyon yıl önce")],
   "Meke Gölü'nün ilk krateri yaklaşık 50 bin yıl önceki bir volkanik patlamayla oluşmuştur."),
  ("B16", "sayi", "yeniden_yaz", [(132, 17, "421 ppm’ye ulaştı")],
   "Atmosferdeki karbondioksit miktarı günümüzde 300 ppm'nin altında seyretmektedir."),
  ("B17", "sayi", "yeniden_yaz", [(87, 4, "2.500-3.000 kalori")],
   "Sağlıklı bir yetişkinin günlük enerji ihtiyacı ortalama 1.000 kalori kadardır."),
  ("B18", "sayi", "yeniden_yaz", [(61, 5, "dört CO₂, altı NADH ve iki FADH₂")],
   "İki Asetil-CoA molekülünün Krebs döngüsüne girmesiyle toplam iki NADH oluşur."),
  ("B19", "en_ilk", "yeniden_yaz", [(64, 9, "en uzun mesafeyi kateden kuş türüdür")],
   "Göç sırasında en uzun mesafeyi kateden kuş türü leyleklerdir."),
  ("B20", "en_ilk", "yeniden_yaz", [(165, 3, "ilk olarak Ege Tarımsal Araştırma")],
   "Ülkemizde alan dışı koruma çalışmaları ilk olarak Karadeniz Tarımsal Araştırma Enstitüsünde başlatılmıştır."),
  ("B21", "en_ilk", "yeniden_yaz", [(24, 9, "besin zincirinin ilk halkasını oluşturur")],
   "Su ekosistemlerinde besin zincirinin ilk halkasını balıklar gibi tüketiciler oluşturur."),
  ("B22", "en_ilk", "yeniden_yaz", [(46, 5, "Midenin ilk bölümünde bulunan bezli midede")],
   "Kuşlarda besinler önce kaslı mideye (taşlık), ardından bezli mideye ulaşır."),
  ("B23", "sozel", "yeniden_yaz", [(51, 3, "besin maddeleri ince bağırsakta emilir")],
   "İnsanda besinlerin emiliminin büyük bölümü mide duvarından gerçekleşir."),
  ("B24", "sozel", "yeniden_yaz", [(105, 2, "organik maddeleri inorganik maddelere dönüştüren")],
   "Ayrıştırıcılar, inorganik maddelerden organik madde üreten ototrof canlılardır."),
  ("B25", "sozel", "yeniden_yaz", [(27, 2, "Fotoliz sonucu serbest kalan oksijen")],
   "Fotolizde suyun parçalanmasıyla oluşan oksijen atmosfere verilmez, tamamı hücrede glikoz sentezinde kullanılır."),
 ],
}
GELISTIRME = {"kitap": 7, "biyoloji10": 8}
MIN_SAYFA_UZAKLIGI = 3

cikti = []
for kitap, ogeler in SET.items():
    bloklar = bloklari_yukle(rf"D:\derskitabı\veri\{kitap}_bloklar.json")
    blok = {(b.sayfa_no, b.blok_no): b for b in bloklar}
    # Başka maddelerin kaynak/hedef blokları, okura hitap eden (etkinlik) paragraflar ve
    # numaralı soru maddeleri hedef olamaz
    kullanilan = {(s, bn) for o in ogeler for s, bn, _ in o[3]} | {o[4][:2] for o in ogeler if isinstance(o[4], tuple)}
    etkinlik = etkinlik_bloklari([b.sozluge() for b in bloklar])
    paragraflar = [b for b in bloklar if b.tur == "paragraf" and len(b.metin.split()) >= 15
                   and (b.sayfa_no, b.blok_no) not in kullanilan
                   and (b.sayfa_no, b.blok_no) not in etkinlik
                   and not any(_YONERGE.search(w.lower()) for w in b.metin.split())
                   and not re.match(r"\s*[\"“(…]*\d+\s*[.)]", b.metin)]
    P = None
    for oid, tur, yontem, kaynaklar, hedef in ogeler:
        for s, bn, parca in kaynaklar:
            assert parca in blok[(s, bn)].metin, (oid, s, bn, parca)
        oge = {"id": oid, "kitap": kitap, "tur": tur, "yontem": yontem,
               "kaynaklar": [{"sayfa_no": s, "blok_no": bn, "parca": p} for s, bn, p in kaynaklar]}
        if yontem == "tekrar_boz":
            s, bn, eski, yeni = hedef
            assert blok[(s, bn)].metin.count(eski) == 1, (oid, eski)
            oge["hedef"] = {"sayfa_no": s, "blok_no": bn, "islem": "degistir", "eski": eski, "yeni": yeni}
        elif isinstance(hedef, tuple):  # elle seçilmiş hedef paragraf (otomatik seçim konu dışı kaldı)
            s, bn, yeni = hedef
            assert blok[(s, bn)].tur == "paragraf", oid
            oge["hedef"] = {"sayfa_no": s, "blok_no": bn, "islem": "ekle", "yeni": yeni,
                            "hedef_paragraf_basi": blok[(s, bn)].metin[:120], "elle_secildi": True}
        else:
            if P is None:
                P = ollama_gomucu([b.metin for b in paragraflar])
            v = ollama_gomucu([hedef])[0]
            kaynak_sayfalari = {s for s, _, _ in kaynaklar}
            adaylar = [(float(P[i] @ v), b) for i, b in enumerate(paragraflar)
                       if (b.sayfa_no, b.blok_no) not in kullanilan and min(abs(b.sayfa_no - s) for s in kaynak_sayfalari) >= MIN_SAYFA_UZAKLIGI
                       and not any(_ETKINLIK.search(x.metin) for x in bloklar
                                   if x.sayfa_no == b.sayfa_no and x.blok_no <= b.blok_no)
                       and not b.metin.rstrip().endswith("?")]
            _, hb = max(adaylar, key=lambda x: x[0])
            kullanilan.add((hb.sayfa_no, hb.blok_no))
            paragraflar_i = [i for i, b in enumerate(paragraflar) if (b.sayfa_no, b.blok_no) not in kullanilan]
            oge["hedef"] = {"sayfa_no": hb.sayfa_no, "blok_no": hb.blok_no, "islem": "ekle", "yeni": hedef,
                            "hedef_paragraf_basi": hb.metin[:120]}
        # Konum: kaynak ya da hedef bir etkinliğin okuma metninde/maddesinde mi? (sonuçlar ayrı raporlanır)
        yerler = [(k["sayfa_no"], k["blok_no"]) for k in oge["kaynaklar"]] + [(oge["hedef"]["sayfa_no"], oge["hedef"]["blok_no"])]
        oge["konum"] = "etkinlik_metni" if any(y in etkinlik for y in yerler) else "duz_metin"
        cikti.append(oge)

rnd = random.Random(20261019)
for kitap, n in GELISTIRME.items():
    kimlikler = [o["id"] for o in cikti if o["kitap"] == kitap]
    secilen = set(rnd.sample(kimlikler, n))
    for o in cikti:
        if o["kitap"] == kitap:
            o["set"] = "gelistirme" if o["id"] in secilen else "test"

Path(sys.argv[1]).write_text(json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter  # noqa: E402
print(len(cikti), Counter(o["set"] for o in cikti), Counter(o["tur"] for o in cikti), Counter(o["yontem"] for o in cikti))
