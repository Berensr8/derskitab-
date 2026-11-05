# Yazım modeli (K33) — sonuçlar

Eğitim 2026-11-05: BERTurk kelime etiketleyici, 205.229 cümle (GECTurk 96.919 + GECTurk'ten yapay 48.746 + Vikipedi gerçek düzeltmeleri 28.148 + kitap cümlelerine yapay hata 31.416), 3 epok, 37 dakika (RTX, bf16). En iyi geliştirme F1 0,955.

Ölçütler ve karar kuralı eğitimden önce yazıldı (KARARLAR K33).

## Ölçümler (bizim model / hazır GECTurk modeli)

| Ölçüm | Bizim | GECTurk hazır |
|---|---|---|
| E1 TDE 10 yapay hatalar (görülmemiş kitap), F1 | **0,913** | 0,205 |
| E2 GECTurk test, F1 | 0,984 | 0,990 |
| E2 film yorumları, F1 | 0,892 | 0,924 |
| E3 Vikipedi gerçek düzeltmeleri (görülmemiş sayfalar), F1 | **0,757** | 0,268 |
| E4 kilitli yazım test seti, recall | **44/56** | 8/56 |
| E5 etiketli gerçek kitap hataları, recall | **20/37** | 0/37 |
| E6 sistemin yanlış alarmlarına "doğru" deme | 275/331 | 317/331 |

E4 türlere göre (bizim): harf düşmesi 10/10, ikileme 11/11, yer değiştirme 10/10, Türkçe harf 10/10; bitişik-ayrı 0/3, noktalama-boşluk 0/6, kelime tekrarı 0/2.

## Karar kuralı

**A — ek dedektör: geçmedi.** Model kitaplarda sistemin bulmadığı 3.430 yeni tespit üretti (10 sayfada 29). Rastgele 60 tanesi olasılıklar görülmeden etiketlendi (`yazim_modeli_e7_etiketler.json`): **1 gerçek** ("Türkistanda" → Türkistan'da), 59 yanlış alarm → isabet 0,017 (eşik 0,50). Yüksek güvenli tespitler de temiz değil (olasılık ≥ 0,99 olan 27 tespitte 0 gerçek).

Yanlış alarmların sebebi: doğru kelime 20 (ölçütleri, Zamir, "teller de", fablıyla), eski metin/alıntı 13 (Göktürk yazıtı, divan şiiri, ağız), PDF okuma 11 (İstiklal Marşı sayfalarında "ı" harfi düşüyor), terim 7, harita etiketi 4, özel isim 4.
Sistemin mevcut süzgeçleri (alıntı, terim, özel isim, PDF) hepsini kusursuz ayıklasa bile kalan 21 tespitin 20'si doğru kelime olurdu → ek deneme yapılmadı.

**B — süzgeç: geçmedi.** Gerçek hata kaybı ≤ 1 olan bir eşik bulunamadı: etiketli gerçek hataların 15'ini model "kesin doğru" sayıyor (olasılık < 0,02). Bunların 11'i noktalamadan sonra boşluk unutulması ("katlandı.Takım"); model kelimeye bakıyor, bu türü hiç görmedi. Kalanlar: "antogonist", "fonsiyonlar", "listeleyi", "sorumluklar", "planınında".

## Sonuç

Model yazım hatası *bulmayı* gerçekten öğrendi: görülmemiş kitapta ve gerçek Vikipedi hatalarında hazır modelden 3–4 kat iyi, kilitli test setinde 8 → 44. Ama gerçek ders kitabında hatalar çok seyrek (sayfada 0–1) ve kitap metni eğitim verisinden farklı (eski metinler, terimler, harita, PDF bozulmaları): model sayfa başına ~3 yanlış alarm veriyor, ürüne girmesi öğretmenin işini artırır. Önceden yazılan kurala göre ürüne girmedi. Yöntem, veri seti ve ölçümler projenin çıktısı olarak kalıyor.
