# Bağımsız Değerlendirme 2 (K42) — Ön Kayıt ve Kilitli Sayfalar (K40)

- **Tarih:** 2026-11-09
- **Amaç:** K39 bağımsız değerlendirmesinde ölçülen yazım denetimi başarısını (isabet 8/40 = %20, bulma oranı 6/21 = %29) geliştirmek ve yapılan iyileştirmeleri kirlenmemiş yeni bir örneklem üzerinde bağımsız olarak sınamak.
- **Rastgelelik tohumu:** `20261110`
- **Kilitli havuz dosyası:** `veri/bagimsiz2/havuz.json` (git dışında tutulur)
- **SHA-256 parmak izi:** `1e96023b2b015f9c87eca7f4a26e431a610fef9afe0dc5bdbe6e86c0cfc36c27`

---

## 1. Ölçüm Yöntemi

Yöntem K39 ile birebir aynı tutulacaktır:
- **A (Sayfa okuma):** ChatGPT ve Gemini, belirlenen 30 adet A sayfasını baştan sona okuyarak sistemden bağımsız olarak yazım ve noktalama hatalarını çıkarır. `testseti/bagimsiz/A_talimat.txt` talimatı değiştirilmeden kullanılır.
- **Karar kurulu:** ChatGPT, Gemini ve DeepSeek'ten oluşan bağımsız kurul tüm adayları (A'dan gelenler ve B'den seçilen sistem tespitleri) oylar.
  - Adaylar karışık sırada ve nötr kimliklerle sunulur (`KURUL_talimat.txt` değiştirilmeden kullanılır).
  - Adayın kaynağı, sistemin güven puanı veya önerisi kurula gösterilmez.
  - Karar çoğunluk oyuyla (en az 2/3 model) belirlenir.
  - Alıntı kuralı aynıdır: alıntı/replik/tarihî metinlerdeki yazar veya dönem üslubu hata sayılmaz (MEB TYMM 2.4.1); dizgi bozulmaları hata sayılır.
- **Kimler etiket koymaz:** Claude (asistan) ve öğrenci etiketleme yapmaz; oylama sonuçları mekanik olarak toplanır.

---

## 2. Kilitli Örneklem ve Havuz

Ölçüm sayfaları `testseti/araclar/k42_havuz.py` ile `20261110` tohumu kullanılarak önceden seçilmiş ve kilitlenmiştir:

### Dışlama Kriterleri
- Kitapların ilk ve son 10 sayfası hariç tutulmuştur (`10 < sayfa_no < son - 10`).
- Daha önce etiketlenmiş veya test amaçlı kullanılmış sayfalar (`derskitabi.yazim_modeli.veri.test_sayfalari()`) hariç tutulmuştur.
- K39 bağımsız değerlendirmesinde kullanılan tüm A sayfaları (`testseti/bagimsiz/A_sayfa_listesi.json`) ve B aday sayfaları (`testseti/bagimsiz/B_anahtar.json`) hariç tutulmuştur.
- B havuzu sayfaları, A sayfaları ile kesinlikle çakışmaz.

### A Sayfaları (Bulma Oranı — 30 sayfa)
En az 150 kelime paragraf içeren uygun sayfalar arasından rastgele 10'ar sayfa:
- **Biyoloji 9 (10 sayfa):** 43, 76, 87, 97, 122, 142, 150, 155, 158, 164
- **Biyoloji 11 (10 sayfa):** 53, 75, 102, 126, 132, 137, 152, 158, 167, 224
- **Türk Dili ve Edebiyatı 10 (10 sayfa):** 68, 74, 76, 84, 106, 215, 237, 240, 277, 292

### B Havuzu (İsabet — 5 kitap x 40 sayfa = 200 sayfa)
Ölçüm anında bu havuzdaki gösterilen (güven ≥ 0,5) sistem tespitlerinden kitap başına 8, toplam 40 rastgele tespit seçilecektir. Buna ek olarak 2. adımda eklenecek her yeni kuraldan havuzda varsa en çok 10 tespit seçilecek ve ayrı raporlanacaktır.
- **Biyoloji 9 (40 sayfa):** 12, 13, 15, 16, 17, 18, 22, 28, 29, 33, 35, 38, 44, 46, 47, 49, 52, 54, 55, 64, 75, 77, 91, 98, 99, 102, 112, 113, 121, 127, 128, 151, 152, 157, 159, 163, 166, 167, 172, 174
- **Biyoloji 11 (40 sayfa):** 13, 14, 19, 20, 21, 22, 25, 26, 33, 45, 47, 55, 64, 68, 69, 76, 77, 86, 87, 92, 100, 107, 110, 112, 123, 124, 127, 136, 138, 161, 162, 163, 169, 186, 190, 192, 193, 199, 212, 217
- **Türk Dili ve Edebiyatı 10 (40 sayfa):** 19, 29, 34, 40, 48, 78, 79, 80, 88, 98, 103, 104, 108, 130, 132, 146, 154, 167, 173, 193, 207, 218, 230, 231, 234, 239, 243, 246, 257, 262, 270, 271, 274, 276, 288, 290, 293, 294, 295, 299
- **Türk Dili ve Edebiyatı 11 (40 sayfa):** 16, 19, 41, 42, 46, 47, 53, 65, 66, 88, 113, 119, 121, 124, 135, 145, 146, 154, 156, 162, 166, 181, 194, 195, 197, 208, 211, 215, 222, 225, 228, 238, 260, 261, 273, 274, 277, 288, 295, 296
- **Türk Dili ve Edebiyatı 12 (40 sayfa):** 11, 13, 18, 20, 38, 54, 55, 65, 76, 82, 85, 86, 105, 124, 131, 132, 135, 137, 139, 141, 164, 170, 171, 175, 176, 178, 185, 188, 189, 200, 203, 208, 212, 236, 237, 238, 239, 240, 255, 257

---

## 3. Disiplin ve Körlük Kuralı

- Geliştirme sürecinde hiçbir betik veya inceleme bu sayfalardaki metne veya bu sayfalardaki sistem çıktısına bakamaz.
- Geliştirmede kullanılan tüm betikler `testseti.araclar.k42_havuz.haric_sayfalar()` fonksiyonuyla bu sayfaları hariç tutar.

---

## 4. Ölçülecek Yapılandırma ve Başarı Ölçütleri

- **Yapılandırma:** Ürünün varsayılan ayarları. Hakem varsayılan olarak açık olduğunda ana sonuç hakemli olacak; hakemsiz sonuç ikincil olarak verilecektir.
- **Önceden sabitlenen başarı ölçütleri:**
  1. B isabeti (kurul çoğunluk oyu ≥ 2/3) **≥ %35** olacaktır.
  2. A bulma oranı (gösterilen tespitler) **≥ %45** olacaktır.
  3. İsabet hiçbir durumda K39'un taban değeri olan **%20'nin altına düşmeyecektir**.
  4. 2. adımda eklenecek yeni kurallardan her birinin kendi isabeti **≥ %50** olmalıdır; %50'nin altında kalan kural üründe düşük önceliğe (güven 0,25) indirilir.
- Sonuç ne çıkarsa çıksın olduğu gibi dürüstçe raporlanacak; bu ölçütler ve eşikler sonradan değiştirilmeyecektir.


---

## 5. Ek (K41-ek): Metin Katmanı Mekanik Kontrolü

- **Gerekçe:** K39 bağımsız değerlendirmesinde kurulun "hata" dediği 21 maddeden 4'ünün (A01: "TAHRIŞ EDICI", A48: "DINLEME", A16: "Anahtarı’’", A25: "”Yüce") basılı sayfada var olmayan, InDesign / PDF dönüştürücüsünün `ActualText` etiketinden veya görsel tırnak dizgisinden kaynaklanan sahte metin katmanı farkları olduğu saptanmıştır.
- **Kural:** Kurula gitmeden önce bütün A ve B adayları için mekanik bir "metin katmanı kontrolü" yapılacaktır:
  - Bir adayın metni, PDF'in glif düzeyindeki karakterlerinden (`page.get_texttrace()`) veya sayfa görüntüsünden farklıysa aday "metin katmanı farkı" olarak ayrılacaktır.
  - Bu tür adaylar ne gerçek hata ne de sistem isabeti sayılacak; hata doğruluk pay ve paydasından çıkarılarak ayrı bir başlık altında raporlanacaktır.
  - Karar kurulu talimatları (`testseti/bagimsiz/A_talimat.txt` ve `KURUL_talimat.txt`) değiştirilmeyecektir.
- Bu ek, bağımsız kurul ölçümünden (K42) önce ön kayıt dosyasına işlenmiştir.
