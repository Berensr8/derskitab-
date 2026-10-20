# Yazım kriteri — test sonuçları (K23)

- **Tarih:** 2026-10-20 · **Kod sürümü:** `9bb37ae` (yazım kriterinde bu ölçüm için hiçbir ayar yapılmadı)
- **Recall seti:** `yazim_hatalari.json` (SHA-256 `097538e7…`), 80 eklenmiş hata (Sosyal Bilgiler 6 ve Biyoloji 10'a 40'ar; 24 geliştirme / 56 test), sabit tohumla üretildi (`araclar/k23_yazim_olustur.py`).
- **Precision seti:** `yazim_etiketler.json` — sistemin değiştirilmemiş kitaplardaki tespitleri elle etiketlendi: Sosyal Bilgiler 6'nın 78 tespitinin hepsi, Biyoloji 10'dan sabit tohumlu 50 tespit (etiketleyen: Claude, kullanıcının yetkisiyle).

## Recall (eklenen hatalar)

| Set | Bulunan | Yüksek güvenle |
|---|---|---|
| Geliştirme | 24/24 (%100) | %96 |
| **Test** | **56/56 (%100)** | %98 |

Her hata türünde %100: Türkçe harf kaybı, harf düşmesi, harf ikilenmesi, yer değiştirme; noktalamadan sonra boşluk, bitişik/ayrı yazım, "yada", de/da uyumu, "te", "ve ve". Eklenen hatalar yeni sahte tespite yol açmadı.

**Bu %100'ü doğru okumak:** Set bilinçli olarak sistemin kapsamındaki hatalardan oluşuyor — kelime dışı yazım hataları (sonuç geçersiz bir kelime) ve TDK kural hataları; küçük harfle başlayan kelimeler, blok ortası. Kapsam dışında kalanlar ölçülmedi ve sistem bunları yakalayamaz: gerçek kelime hataları ("bende geldim" → "ben de"), büyük harfle başlayan kelimelerdeki hatalar (özel isim sanılıp atlanıyor), kitapta 3 kez ve fazla tekrarlanan hatalar (terim sanılıyor).

## Precision (gerçek tespitler)

| | Sosyal Bilgiler 6 | Biyoloji 10 |
|---|---|---|
| Etiketlenen | 78 (12 belirsiz) | 50 |
| **Precision** (belirsizler hariç) | **20/66 = %30** | **3/50 = %6** |
| Yalnız yüksek güven (1,0) | 17/41 = %41 | 3/32 = %9 |
| TDK kural tespitleri | 6/7 | 2/2 |

**Sahte tespitlerin sebepleri (iki kitap):** araçların bilmediği bilimsel/tarihî terimler 43, araçların tanımadığı doğru kelimeler ("ithafen", "gluten", "nelerin"…) 31, eski yazımlı alıntılar (İstiklal Marşı, Gençliğe Hitabe, tarihî metinler) 9, PDF okuma sorunları 3, harita etiketleri 2, özel isimler 3, sayı parçaları 2.

**Belirsiz (12):** "(…)" öncesi boşluk (tasarım tercihi), "nesilden nesile", "oğula", "tezhib" (alıntı olabilir), "dü şünme" (dizgi mi PDF mi belirsiz).

## Yorum

- Sistem gerçek hataları yakalıyor (Sosyal 6'da 20 gerçek hata: "kisisel gelisimimiz", "jandama", "kullanmışladır", "planınında", "değiştokuş" ve 9 noktalama hatası), ama kelime denetimi bir **aday listesi** üretiyor: özellikle terim yoğun kitaplarda (Biyoloji) bir insanın gözden geçirmesi gerekir.
- TDK kuralları neredeyse hatasız; asıl iyileştirme alanı kelime denetimindeki terimler ve alıntılar (Faz 2 fikirleri: F2 alıntıları ayırma, F3 tartışmalı kelimeler için dil modeli hakemi, alan terim sözlükleri).
- Etiketler bundan sonra yapılacak iyileştirmeler için geliştirme verisi sayılmalı; iyileştirilmiş sistemin precision'ı başka kitaplardan yeni etiketlenmiş bir örneklemle ölçülmeli.
