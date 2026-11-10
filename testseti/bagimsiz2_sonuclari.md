# Bağımsız değerlendirme 2: yazım (K42, 2026-11-10)

**Neden:** K39 bağımsız değerlendirmesinde yazım denetimi başarısı bağımsız kurulca ilk kez ölçülmüştü (isabet 8/40 = %20, bulma oranı 6/21 = %29). Ardından K40'ta yeni bir kilitli havuz ayrıldı, K41'de eksik kurallar eklendi, K41-ek ve K41-ek4 adımlarında PDF okuma katmanındaki hatalar (I/İ dönüşümü, görünür kısa çizgi, satır sonu boşlukları) düzeltildi. Bu çalışma (K42), yapılan iyileştirmeleri kirlenmemiş yeni bir örneklem üzerinde bağımsız olarak sınamaktadır.

Ön kayıt belgesi: `testseti/k42_on_kayit.md`. Sistemin kilitli çıktıları ve parmak izleri kurul oylamasından önce kilitlendi (`testseti/bagimsiz2_kilit.txt`, commit `9c28fe7` ve `722dad7`).

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
| **Hakemli (Ürün varsayılanı — Ana Sonuç)** | **7/25 = %28,0** (%14,3–%47,6) | K39: 8/40 = %20,0 (+8,0 puan) |
| Oybirliği (3/3 model "HATA") | 5/25 = %20,0 (%8,9–%39,1) | K39: 4/40 = %10,0 (+10,0 puan) |
| En az bir model "HATA" dedi | 11/25 = %44,0 (%26,7–%62,9) | K39: 18/40 = %45,0 |
| **Hakemsiz (İkincil Sonuç)** | **5/29 = %17,2** (%7,6–%34,5) | Hakem katkısı: **+10,8 puan** |

- **Ön kayıt hedefleriyle karşılaştırma:**
  - Taban şartı sağlandı: İsabet %20 taban değerinin altına düşmedi (%28,0 > %20,0).
  - İddialı hedef sağlanamadı: Ön kayıtta hedeflenen %35 eşiğinin altında kalındı (%28,0).
  - Hakem etkisi belirgin: Yapay zekâ hakemi (`gemma4`), yanlış alarmları eleyerek isabeti %17,2'den %28,0'a çıkardı.

- **Güven düzeyine göre (Hakemli):**
  - Güven 1,0 ("öncelikli"): 1/10 = %10,0 (B37 "sürdürülenilmesi"; diğer 9 aday alıntı veya PDF dizgi birleşmesidir).
  - Güven 0,75: 1/8 = %12,5 (B22 "çoşkulu").
  - Güven 0,5 ("kontrol edilecek"): 5/7 = **%71,4** (B01 "güvenirliliğini", B07 "SEBEPLERI", B30 "sorumluklar", B34 "BENZERLIKLERIN", B38 "BENZERLIKLER").

- **Kitaba göre (Hakemli):**
  - **Biyoloji 9:** 2/2 = %100 (B30 "sorumluklar", B37 "sürdürülenilmesi").
  - **Biyoloji 11:** 1/1 = %100 (B01 "güvenirliliğini").
  - **TDE 10:** 3/6 = %50,0 (B07 "SEBEPLERI", B34 "BENZERLIKLERIN", B38 "BENZERLIKLER").
  - **TDE 11:** 0/7 = %0,0 (tespitlerin tamamı eski metin/şiir alıntısı: budunuğ, törüsin, bolsar, kılbirleşik, yitü, tutsıkıngındevlet, üzre).
  - **TDE 12:** 1/9 = %11,1 (B22 "çoşkulu"; diğerleri alıntı ve TDK'de geçerli kelimeler: seçik, püskü, nefs, orda, duymayagöreyim, Allahın, içeliği, gezegen’in).

- **Hakemli sistemin bulduğu 7 gerçek hata:**
  1. `sürdürülenilmesi` (Biyoloji 9 s.99) — Ek hatası / anlatım bozukluğu (doğrusu: sürdürülmesi / sürdürülebilmesi).
  2. `sorumluklar` (Biyoloji 9 s.12) — Eksik harf (doğrusu: sorumluluklar).
  3. `güvenirliliğini` (Biyoloji 11 s.212) — Yanlış türetim / ek yığılması (doğrusu: güvenirliğini / güvenilirliğini).
  4. `SEBEPLERI` (TDE 10 s.299) — Büyük harfte I/İ karışması (`buyuk_harf_i` kuralı).
  5. `BENZERLIKLER` (TDE 10 s.299) — Büyük harfte I/İ karışması (`buyuk_harf_i` kuralı).
  6. `BENZERLIKLERIN` (TDE 10 s.299) — Büyük harfte I/İ karışması (`buyuk_harf_i` kuralı).
  7. `çoşkulu` (TDE 12 s.124) — Yanlış ünsüz (doğrusu: coşkulu).

- **Yanlış alarmların ana kaynakları:**
  - Edebiyat kitaplarındaki (TDE 11 ve 12) eski Türkçe, halk ağzı ve şiir alıntıları.
  - Satır sonunda bölünmüş kelimelerin birleşmesi (örn. "açılarını de-", "kılbirleşik").
  - TDK sözlüğünde yer alan ancak morfolojik çözümleyicinin tanımadığı nadir sözcükler ("seçik", "içeliği").

---

### 2. Yeni kuralların isabeti (K41)

Ön kayıt kuralı: 2. adımda eklenen kuralların kendi isabeti en az %50 olmalıdır; altında kalanlar düşük önceliğe (0,25) indirilir.

| Kural (`alt_tur`) | Havuzdaki Tespit Sayısı | Kurulun HATA Dediği | İsabet | Karar |
|---|---|---|---|---|
| `buyuk_harf_i` | 3 | 3 | **3/3 = %100,0** | **Kural onaylandı** (≥ %50 şartını geçti) |
| `dizgi_rakam_harf` | 0 | - | - | Havuzda tespit yok |
| `duzeltme_isareti_nispet` | 0 | - | - | Havuzda tespit yok |
| `noktalama_cift_tek_tirnak` | 0 | - | - | Havuzda tespit yok |
| `noktalama_parantez_cift_nokta` | 0 | - | - | Havuzda tespit yok |
| `noktalama_ters_tirnak` | 0 | - | - | Havuzda tespit yok |

`buyuk_harf_i` kuralı 3'te 3 yaparak kusursuz çalıştı. Diğer 5 kural 200 sayfalık bağımsız havuzda yanlış alarm üretmedi. Düşük önceliğe indirilecek hiçbir yeni kural yoktur.

---

### 3. Bulma oranı: sayfalardaki gerçek hataların kaçını buldu? (A)

- Bağımsız kurul, 30 kilitli A sayfasında ChatGPT ve Gemini'nin getirdiği 82 adaydan **17 tanesine "HATA"** dedi (hepsi PDF metin katmanında doğrulanmış gerçek hatalardır).
- **Sonuç:**

| Yapılandırma | Gerçek Hata Sayısı | Sistemin Gösterdiği (Güven ≥ 0,5) | Bulma Oranı (Recall) (%95 Wilson) |
|---|---|---|---|
| **Hakemli (Varsayılan)** | 17 | 0 | **0/17 = %0,0** (%0,0–%18,4) |
| **Hakemsiz** | 17 | 0 | **0/17 = %0,0** (%0,0–%18,4) |

- **Ön kayıt hedefiyle karşılaştırma:** Ön kayıtta hedeflenen ≥ %45 şartı sağlanamadı (%0,0).
- **Neden sıfır çıktı?**
  K39'da bulunan 6 hatanın 5'i tek bir sayfadaki (Biyoloji 9 s.114) toplu Türkçe karakter bozulmalarından ("molekullerinin", "gecirgen" vb.) ibaretti. Bağımsız seçilen bu 30 yeni sayfada ise bu tarz toplu harf kayıpları bulunmamaktadır. Kurulun belirlediği 17 gerçek hata şu türlerdendir:
  1. **Aralık boşluğu / noktalama boşluksuzluğu (5):** "Form11", "11,12, 13", "1947,1962", "Yönerge :", "yazınız..".
  2. **Yabancı / Latince taksonomi terimleri (3):** "Commasie" (Coomassie), "Canis familaris", "Canidea".
  3. **Noktalama işareti hataları (3):** "akıllı termostatlar;", "solunum hızı;", "örnek veriniz?".
  4. **Tek başına geçerli Türkçe kelime olan dizgi/anlatım hataları (3):** "Sözlü alarak" (olarak), "Kap atışı" (kalp atışı), "bir takım" (birtakım).
  5. **Kısaltma standardı (1):** "gr" (g olmalı).
  6. **Kelime türetimi (1):** "coğrafik" (coğrafi).
  7. **Alıntı içi dizgi (1):** "’abesdir".

  Bu hata türleri ya sistemin kapsamı dışındadır (aralık boşluğu kuralı henüz tüm noktalama ve formül kalıplarını kapsamaz, Latince terim sözlüğü yoktur) ya da tek başına sözlükte geçerli kelime oldukları için morfoloji motorunca hata olarak algılanmaz.

---

### 4. Kurulun kendi içindeki uyumu

- **İkili ham uyum:**
  - ChatGPT – Gemini: **%92,5**
  - ChatGPT – DeepSeek: **%74,2**
  - Gemini – DeepSeek: **%73,3**
- **Üçünün de aynı oyu verdiği aday:** 84 / 120 (%70,0).
- **Fleiss κ:** **0,471** (Orta düzey uyum). K39'daki κ = 0,33 değerine göre kurul uyumu belirgin biçimde artmıştır.

---

### 5. K39 ve K42 Yan Yana Karşılaştırması

| Boyut | K39 Bağımsız Değerlendirme 1 | K42 Bağımsız Değerlendirme 2 | Değişim / Yorum |
|---|---|---|---|
| **B İsabeti (Hakemli)** | 8/40 = %20,0 (%10–35) | **7/25 = %28,0** (%14,3–%47,6) | **+8,0 yüzde puan arttı** |
| **B İsabeti (Hakemsiz)** | 8/40 = %20,0 | **5/29 = %17,2** (%7,6–%34,5) | Hakem katkısı: +10,8 puan |
| **B İsabeti (Fen Kitapları)** | 3/16 = %18,8 | **3/3 = %100,0** | Fen kitaplarında yanlış alarm çok azaldı |
| **B İsabeti (Edebiyat)** | 5/24 = %20,8 | 4/22 = %18,2 | Alıntılardan kaynaklanan zorluk devam ediyor |
| **Yeni Kural İsabeti** | - | `buyuk_harf_i`: **3/3 = %100,0** | Kusursuz çalıştı |
| **A Bulma Oranı (Recall)** | 6/21 = %28,6 (%14–50) | **0/17 = %0,0** (%0,0–%18,4) | Doğal hatalarda sistemin kapsam darlığı ortaya çıktı |
| **Kurul Uyumu (Fleiss κ)** | 0,33 (Zayıf/orta) | **0,471** (Orta) | Kurul çok daha tutarlı çalıştı |

---

## Sonuç ve Çıkarımlar

1. **İsabet arttı (%20 → %28):** Yapay zekâ hakemi (`gemma4`) ve K41'deki kural düzeltmeleri sayesinde gösterilen tespitlerde gerçek hata oranı yükseldi. Özellikle fen kitaplarında (Biyoloji 9 ve 11) hakemli çıktıda isabet 3'te 3 (%100) oldu.
2. **Edebiyat kitapları alıntı sorunu:** TDE 11 ve TDE 12 kitaplarında gösterilen tespitlerin çoğu eski Türkçe, divan şiiri veya dönemin üslubuna ait sözcüklerdir. Hakem bu kelimelerin bir kısmını elese de tamamını ayırt edememektedir.
3. **Bulma oranının gerçekliği:** Sistem, bilerek üretilmiş test setlerinde yüksek başarı gösterse de, ders kitaplarındaki doğal hatalarda (aralık boşluğu, Latince isimler, cümle içi bağlamsal kelime karışmaları) bulma oranı oldukça düşüktür (%0). Kullanıcı arayüzünde "bulma oranı düşüktür / sistem her hatayı yakalayamaz" uyarısı net bir şekilde korunmalıdır.

---

## Dosyalar ve Parmak İzleri

- Kilit dosyası: `testseti/bagimsiz2_kilit.txt`
- Kurul sonuçları: `veri/bagimsiz2/kurul_sonuc.json`
- Ham oylar: `bagimsiz_degerlendirme2/Kurul_GPT.txt`, `Kurul_Gemini.txt`, `Kurul_DeekSeek.txt`
- Anahtarlar: `veri/bagimsiz2/kurul_anahtar.json`, `A_birlesik_anahtar.json`, `B_anahtar.json`, `A_sistem_gizli.json`
- Araçlar: `testseti/araclar/k42_*.py`
