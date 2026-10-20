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

---

# Yazım hakemi ile (K25, F3)

- **Tarih:** 2026-10-20 · **Kod sürümü:** `76d613d` (ayarlar donduruldu; sonrasında yalnız bellek bekçisi eklendi)
- **Yöntem:** Kelime denetiminin her tespiti cümlesiyle gemma4'e sorulur. "Doğru" derse tespit silinmez, güveni 0,25'e iner (düşük öncelik); "hata" derse korunur ve doğru yazım önerilir. Kelime, kitapta geçen bir kelimeye tek yazım hatası uzaklıktaysa model "doğru" dese de düşürülmez (model küçük hataların üzerinden okuyabiliyor: "jandama"yı "jandarma" sandı). TDK kural tespitlerine dokunulmaz. Aşağıdaki sayılar **gösterilen** (güven ≥ 0,5) tespitler içindir.
- **Precision test etiketleri** (Matematik 11, TDE 9) hakem hiç çalıştırılmadan etiketlenip commit edildi (`bdf0e4d`).

| | Hakemsiz | Hakemli |
|---|---|---|
| Recall, geliştirme (24) | 24/24 | 23/24 |
| **Recall, test (56)** | 56/56 | **55/56** |
| Sosyal 6 (geliştirme): gerçek / gösterilen (belirsiz hariç) | 20/66 = %30 | 20/30 = **%67** |
| Biyoloji 10 (geliştirme) | 3/50 = %6 | 3/10 = **%30** |
| **Matematik 11 (test)** | 8/35 = %23 | 7/26 = **%27** |
| **TDE 9 (test)**: gösterilen sahte tespit | 39 | **13** |
| Düşük önceliğe inen gerçek hata | — | geliştirme 0, test 1 ("olacacağını") |

**Yorum:** Hakem, terim ve alıntı yoğun kitaplarda gürültüyü büyük ölçüde azaltıyor (TDE 9: 39 → 13 sahte; Sosyal 6: 46 → 10; Biyoloji 10: 47 → 7) ve recall'ı neredeyse koruyor. Matematik'te kazanç küçük: oradaki sahte tespitlerin çoğu PDF okuma parçaları ("lmak", "dikd", derece işaretinin "c" okunması); model bunlara "belirsiz" diyor ve tespit gösterilmeye devam ediyor. "Belirsiz" kararlarının da önceliğini düşürmek bir sonraki iyileştirme adayıdır — test sonucu görüldüğü için ancak yeni bir test örneklemiyle ölçülebilir.
