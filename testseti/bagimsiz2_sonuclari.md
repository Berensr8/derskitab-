# Bağımsız değerlendirme 2: yazım (K42, 2026-11-10)

> **Düzeltme notu (2026-11-24, K50):** Kurulun "hata" dediği üç `buyuk_harf_i` tespiti (`SEBEPLERI`,
> `BENZERLIKLER`, `BENZERLIKLERIN`, TDE 10 s. 299) basılı sayfada noktalı İ ile doğru yazılmıştır; yalnız PDF'in
> metin katmanı "I" diyor (glifin gerçek kutusu ve sayfa görüntüsüyle doğrulandı). Kurul yalnız metni gördüğü
> için bunları hata saydı. Basılı sayfaya göre hakemli isabet **7/25 değil 4/25 (%16)**, `buyuk_harf_i` kuralı
> **3/3 değil 0/3**'tür. Aşağıdaki sayılar kurulun özgün oylamasıdır, değiştirilmedi.

**Neden:** K39 bağımsız değerlendirmesinde yazım denetimi başarısı bağımsız kurulca ilk kez ölçülmüştü (düzeltilmiş sayılarla isabet 7/40 = %17,5, bulma oranı 6/17 = %35,3; ilk ham sonuçlar: 8/40 = %20, 6/21 = %29). Ardından K40'ta yeni bir kilitli havuz ayrıldı, K41'de eksik kurallar eklendi, K41-ek ve K41-ek4 adımlarında PDF okuma katmanındaki hatalar (I/İ dönüşümü, görünür kısa çizgi, satır sonu boşlukları) düzeltildi. Bu çalışma (K42), yapılan iyileştirmeleri kirlenmemiş yeni bir örneklem üzerinde bağımsız olarak sınamaktadır.

Ön kayıt belgesi: `testseti/k42_on_kayit.md`. Sistemin kilitli çıktıları ve parmak izleri kurul oylamasından önce kilitlendi (`testseti/bagimsiz2_kilit.txt`, commit `9c28fe7` ve `722dad7`).

---

## Ön Kayıt Başarı Ölçütleri Karşılama Tablosu

| No | Ön Kayıt Ölçütü | Hedef | Gerçekleşen | Durum |
|---|---|---|---|:---:|
| 1 | B İsabeti (Kurul çoğunluk oyu $\ge$ 2/3) | $\ge$ %35 | 7/25 = **%28,0** (%14,3–%47,6) | **✗** |
| 2 | A Bulma Oranı (Gösterilen tespitler) | $\ge$ %45 | 0/17 = **%0,0** (%0,0–%18,4) | **✗** |
| 3 | Taban İsabet | Hiçbir durumda K39 tabanının (%20) altına düşmeyecek | Nokta tahmini: **%28,0** > %20,0; Wilson alt sınırı: **%14,3** | **✓ (zayıf)** |
| 4 | Yeni Kuralların İsabeti | Her kuralın kendi isabeti $\ge$ %50 | `buyuk_harf_i`: **3/3 = %100,0**; diğer 5 kuralda tespit yok | **Yalnız bir kural için ✓** |

- Ölçüt 3 (taban şartı) nokta tahmini düzeyinde (%28,0 > %20,0) sağlanmış görünse de Wilson %95 alt sınırı %14,3 olduğu için tabanın sağlandığı kesin değildir.
- Ölçüt 4 ise havuzda yalnızca `buyuk_harf_i` tespit ürettiği için diğer kurallar açısından ölçülememiştir.

---

## Yöntem

- **Ölçülen sistem:** K41-ek4 sürümü (commit `854559a`). Ürünün varsayılan yapılandırması: yazım hakemi açık (Ollama + `gemma4:12b-it-qat` hazır). Ana sonuç hakemli çıktıdır; hakemin etkisi görmek için hakemsiz çıktı da ikincil olarak hesaplanmıştır.
- **A, bulma oranı (30 kilitli sayfa):**
  - Biyoloji 9, Biyoloji 11 ve TDE 10 kitaplarından daha önce görülmemiş, en az 150 kelime paragraf içeren 10'ar sayfa (S01–S30; tohum `20261110`).
  - ChatGPT ve Gemini bu sayfaları sistemden bağımsız okuyarak yazım ve noktalama hatalarını çıkardı (`A_talimat.txt`).
  - İki modelin bulguları birleştirildi: 82 aday (kitapta zaten önerilen şekilde yazılı olan 2 aday elendi; mekanik metin katmanı kontrolüyle gliflerle birebir eşleştiği doğrulandı).
- **B, isabet (200 kilitli sayfa):**
  - 5 kitaptan 40'ar sayfalık (toplam 200 sayfa) kilitli havuzdaki tüm gösterilen (güven ≥ 0,5) tespitler alındı.
  - Hakemli sistemde 25 tespit, hakemsiz sistemde 29 tespit çıktı (16'sı ortak). Yeni eklenen `buyuk_harf_i` kuralından havuza düşen 3 tespit de dahil olmak üzere toplam 38 benzersiz aday oluştu.
- **Karar kurulu:**
  - Üç bağımsız yapay zekâ modeli oyladı: ChatGPT, Gemini ve DeepSeek.
  - Toplam 120 aday (A'dan 82, B'den 38), tohum `20261110` ile karıştırılarak kaynağı gizlenmiş nötr kimliklerle (`K001`…`K120`) kurula sunuldu (`KURUL_talimat.txt`).
  - Karar kuralı: en az 2/3 çoğunluk oyu (2 veya 3 model "HATA" derse HATA; 2 veya 3 model "HATA DEĞİL" derse DEGIL; aksi halde BELIRSIZ).
  - Alıntı kuralı (MEB TYMM 2.4.1): alıntı/eski metindeki yazar veya dönem yazımı hata sayılmaz; dizgi kazaları alıntıda da hatadır.

---

## Sonuçlar

### 1. İsabet: sistemin gösterdiklerinin kaçı gerçek hata? (B)

| Yapılandırma / Ölçü | Sonuç (%95 Wilson aralığı) | K39 ile Karşılaştırma |
|---|---|---|
| **Hakemli (Ürün varsayılanı — Ana Sonuç)** | **7/25 = %28,0** (%14,3–%47,6) | K39 düzeltilmiş: 7/40 = %17,5 (%8,7–%31,9) *(ilk ham sonuç: 8/40 = %20)* |
| Oybirliği (3/3 model "HATA") | 5/25 = %20,0 (%8,9–%39,1) | K39: 4/40 = %10,0 (%4–%23) |
| En az bir model "HATA" dedi | 11/25 = %44,0 (%26,7–%62,9) | K39: 18/40 = %45,0 (%31–%60) |
| **Hakemsiz (İkincil Sonuç)** | **5/29 = %17,2** (%7,6–%34,5) | K39 düzeltilmiş: 7/40 = %17,5 |

- **Hakem Etkisinin Değerlendirilmesi:**
  - Hakemli sistemde 7/25 (%14,3–%47,6), hakemsiz sistemde 5/29 (%7,6–%34,5) çıkmıştır. İki oranın Wilson %95 güven aralıkları birbiriyle geniş biçimde çakışmaktadır; bu nedenle mevcut örneklem büyüklüğünde aradaki fark istatistiksel olarak anlamlı değildir.
  - Ancak hakemin ayıklama mekanizması incelendiğinde somut bir fayda görülmektedir: Hakemsiz sistemde gösterilip hakem tarafından düşük önceliğe indirilerek gizlenen **13 tespitin 13'ü de** kurul tarafından "HATA DEĞİL" (DEGIL) olarak değerlendirilmiştir (hiçbir gerçek hata hakem tarafından yanlışlıkla gizlenmemiştir).
- **İsabet Tabanı (%20):**
  - Nokta tahmini %28,0 > %20,0'dir; ancak Wilson %95 alt sınırı %14,3 olduğundan tabanın sağlandığı kesin değildir.
- **Alan Dağılımı (Hakemli):**
  - **Fen kitapları:** 3/3 = %100 (Biyoloji 9: 2/2, Biyoloji 11: 1/1). Ancak örneklem çok küçüktür (3 tespit), bu nedenle "fen kitaplarında isabet %100 veya çok yüksektir" şeklinde genelleştirilerek yorumlanamaz.
  - **Edebiyat kitapları:** 4/22 = %18,2 (TDE 10: 3/6, TDE 11: 0/7, TDE 12: 1/9). Edebiyat kitaplarında alıntılar ve dönemin özgün dil biçimleri nedeniyle yanlış alarm üretimi devam etmektedir.

- **Hakemli sistemin bulduğu 7 gerçek hata:**
  1. `sürdürülenilmesi` (Biyoloji 9 s.99) — Ek hatası / anlatım bozukluğu (doğrusu: sürdürülmesi / sürdürülebilmesi).
  2. `sorumluklar` (Biyoloji 9 s.12) — Eksik harf (doğrusu: sorumluluklar).
  3. `güvenirliliğini` (Biyoloji 11 s.212) — Yanlış türetim / ek yığılması (doğrusu: güvenirliğini / güvenilirliğini).
  4. `SEBEPLERI` (TDE 10 s.299) — Büyük harfte I/İ karışması (`buyuk_harf_i` kuralı).
  5. `BENZERLIKLER` (TDE 10 s.299) — Büyük harfte I/İ karışması (`buyuk_harf_i` kuralı).
  6. `BENZERLIKLERIN` (TDE 10 s.299) — Büyük harfte I/İ karışması (`buyuk_harf_i` kuralı).
  7. `çoşkulu` (TDE 12 s.124) — Yanlış ünsüz (doğrusu: coşkulu).

- **Yanlış alarmların ana kaynakları:**
  - Edebiyat kitaplarındaki (TDE 11 ve 12) eski Türkçe, halk ağzı ve şiir alıntıları (*yoğruşur, tutsıkıngındevlet, püskü, üzre, nefs, hoplaşır, orda, budunuğ, yitü, törüsin, bolsar, gezegen’in, Allahın*).
  - Satır sonunda bölünmüş kelimelerin birleşmesi ("açılarını de-", "kılbirleşik").
  - TDK sözlüğünde yer alan ancak morfolojik çözümleyicinin tanımadığı nadir sözcükler ("seçik", "içeliği").

---

### 2. Güven Düzeyi Sırası Ters

Sistemde tespitlere atanan güven skoru ile bağımsız kurulun bulduğu gerçek hata isabeti karşılaştırıldığında sıralamanın tamamen ters işlediği görülmüştür:

| Güven Skoru | Arayüzdeki Öncelik | B Havuzundaki Tespit | Kurulun HATA Dediği | İsabet Oranı |
|---|---|---|---|---|
| **1,0** | "Öncelikli" | 10 | 1 | **1/10 = %10,0** |
| **0,75** | "Kontrol edilecek" | 8 | 1 | **1/8 = %12,5** |
| **0,5** | "Kontrol edilecek" | 7 | 5 | **5/7 = %71,4** |

- Güven 1,0 alan 10 tespitin 9'u eski metin alıntısı veya satır birleştirme sorunudur; yalnızca 1'i gerçek hatadır (`sürdürülenilmesi`).
- Buna karşılık en yüksek isabet (%71,4) güven 0,5 seviyesinde elde edilmiştir (`güvenirliliğini`, `sorumluklar` ve 3 adet `buyuk_harf_i` tespiti).
- **Çıkarım:** Üründeki "öncelikli" (güven 1,0) etiketi şu an güvenilir değildir; gerçek hataların çoğu güven 0,5'te toplanmaktadır. Bu ölçüm anında üründe öncelik formülleri değiştirilmemiş, gelecekte ele alınacak bir iyileştirme işi olarak kaydedilmiştir.

---

### 3. Yeni Kuralların İsabeti (K41)

Ön kayıt kuralı: 2. adımda eklenen kuralların kendi isabeti en az %50 olmalıdır; altında kalanlar düşük önceliğe (0,25) indirilir.

| Kural (`alt_tur`) | Havuzdaki Tespit Sayısı | Kurulun HATA Dediği | İsabet | Karar |
|---|---|---|---|---|
| `buyuk_harf_i` | 3 | 3 | **3/3 = %100,0** | **Kural onaylandı** (≥ %50 şartını geçti) |
| `dizgi_rakam_harf` | 0 | - | - | Havuzda tespit üretmedi (ölçülemedi) |
| `duzeltme_isareti_nispet` | 0 | - | - | Havuzda tespit üretmedi (ölçülemedi) |
| `noktalama_cift_tek_tirnak` | 0 | - | - | Havuzda tespit üretmedi (ölçülemedi) |
| `noktalama_parantez_cift_nokta` | 0 | - | - | Havuzda tespit üretmedi (ölçülemedi) |
| `noktalama_ters_tirnak` | 0 | - | - | Havuzda tespit üretmedi (ölçülemedi) |

- `buyuk_harf_i` kuralı 3'te 3 yaparak kusursuz çalışmıştır.
- Diğer 5 kural 200 sayfalık kilitli havuzda hiç tespit üretmemiştir; bu nedenle isabetleri ölçülememiş, ön kayıttaki 4. ölçüt yalnızca `buyuk_harf_i` kuralı için değerlendirilebilmiştir. Düşük önceliğe indirilecek bir kural bulunmamaktadır.

---

### 4. Bulma Oranı: sayfalardaki gerçek hataların kaçını buldu? (A)

- Bağımsız kurul, 30 kilitli A sayfasında ChatGPT ve Gemini'nin getirdiği 82 adaydan **17 tanesine "HATA"** dedi (hepsi PDF metin katmanında doğrulanmış gerçek basım hatalarıdır).
- **Sonuç:**

| Kapsam | Gerçek Hata Sayısı | Sistemin Yakaladığı | Bulma Oranı (Recall) (%95 Wilson) |
|---|---|---|---|
| **Gösterilen Tespitler (Güven $\ge$ 0,5)** | 17 | 0 | **0/17 = %0,0** (%0,0–%18,4) |
| **Düşük Öncelikliler Dahil (Güven $\ge$ 0,25)** | 17 | 1 | **1/17 = %5,9** (%0,3–%26,9) |

- Düşük öncelikliler dahil edildiğinde tek eşleşen tespit S25 s.106'daki A36 `’abesdir` -> `abestir` adayıdır (sistem bunu morfolojide 0,25 güven skoruyla üretmiş ancak arayüzde gizlemiştir; alıntı içindedir).
- **Ön kayıt hedefiyle karşılaştırma:** Ön kayıtta hedeflenen $\ge$ %45 şartı sağlanamamıştır (%0,0).
- **Neden sıfır çıktı?**
  K39'da bulunan 6 hatanın 5'i tek bir sayfadaki (Biyoloji 9 s.114) toplu Türkçe karakter bozulmalarından ibaretti. Bağımsız seçilen bu 30 yeni sayfada ise bu tarz toplu harf kayıpları bulunmamaktadır. Kurulun belirlediği 17 gerçek hata şu kategorilerdendir:
  1. **Aralık boşluğu / noktalama boşluksuzluğu (5):** "Form11", "11,12, 13", "1947,1962", "Yönerge :", "yazınız..".
  2. **Yabancı / Latince taksonomi terimleri (3):** "Commasie" (Coomassie), "Canis familaris", "Canidea".
  3. **Noktalama işareti hataları (3):** "akıllı termostatlar;", "solunum hızı;", "örnek veriniz?".
  4. **Tek başına geçerli Türkçe kelime olan dizgi/anlatım hataları (3):** "Sözlü alarak" (olarak), "Kap atışı" (kalp atışı), "bir takım" (birtakım).
  5. **Kısaltma standardı (1):** "gr" (g olmalı).
  6. **Kelime türetimi (1):** "coğrafik" (coğrafi).
  7. **Alıntı içi dizgi (1):** "’abesdir".

  Bu kategoriler sistemin mevcut denetim kapsamının dışındadır; sistem sözlükte tek başına geçerli olan kelimeleri veya Latince terim dizgilerini denetlemez.

---

### 5. Kurulun Kendi İçindeki Uyumu

- **İkili ham uyum:**
  - ChatGPT – Gemini: **%92,5**
  - ChatGPT – DeepSeek: **%74,2**
  - Gemini – DeepSeek: **%73,3**
- **Üçünün de aynı oyu verdiği aday:** 84 / 120 (%70,0).
- **Fleiss κ:** **0,471** (Orta düzey uyum). K39'daki κ = 0,33 değerine göre kurul uyumu belirgin biçimde artmıştır.

---

### 6. K39 ve K42 Yan Yana Karşılaştırması

| Boyut | K39 Bağımsız Değerlendirme 1 (Düzeltilmiş) | K42 Bağımsız Değerlendirme 2 | Değişim / Yorum |
|---|---|---|---|
| **B İsabeti (Hakemli)** | 7/40 = **%17,5** (%8,7–%31,9) *(ham %20)* | **7/25 = %28,0** (%14,3–%47,6) | Nokta tahmini +10,5 puan arttı; güven aralıkları çakışıyor |
| **B İsabeti (Hakemsiz)** | 7/40 = **%17,5** (%8,7–%31,9) *(ham %20)* | **5/29 = %17,2** (%7,6–%34,5) | Hakemsiz isabet aynı düzeyde kaldı |
| **Hakemin Gizlediği Tespitler** | - | 13/13 = %100 Hata Değil | Hakem hiçbir gerçek hatayı yanlışlıkla gizlemedi |
| **Yeni Kural İsabeti** | - | `buyuk_harf_i`: **3/3 = %100,0** | Kural tam isabetle çalıştı |
| **A Bulma Oranı (Gösterilen)** | 6/17 = **%35,3** (%17,3–%58,7) *(ham %28,6)* | **0/17 = %0,0** (%0,0–%18,4) | Doğal hatalarda sistem kapsamının darlığı görüldü |
| **A Bulma Oranı (Gizliler Dahil)**| 8/17 = **%47,1** *(ham %38)* | **1/17 = %5,9** (%0,3–%26,9) | A36 `’abesdir` düşük öncelikte yakalandı |
| **Kurul Uyumu (Fleiss κ)** | 0,33 (Zayıf/orta) | **0,471** (Orta) | Kurul çok daha tutarlı çalıştı |

---

## Dosyalar ve Parmak İzleri

- Kilit dosyası: `testseti/bagimsiz2_kilit.txt`
- Kurul sonuçları: `veri/bagimsiz2/kurul_sonuc.json`
- Ham oylar: `bagimsiz_degerlendirme2/Kurul_GPT.txt`, `Kurul_Gemini.txt`, `Kurul_DeekSeek.txt`
- Anahtarlar: `veri/bagimsiz2/kurul_anahtar.json`, `A_birlesik_anahtar.json`, `B_anahtar.json`, `A_sistem_gizli.json`
- Araçlar: `testseti/araclar/k42_*.py`
