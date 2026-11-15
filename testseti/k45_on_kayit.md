# Bağımsız Değerlendirme 3 (K45) — Ön Kayıt ve Kilitli Sayfalar

- **Tarih:** 2026-11-15
- **Amaç:** K44 yazım iyileştirmelerinin (`ba44473`) geliştirme verisinde görülen etkisini (isabet 7/25 → 7/16, bulma 0/17 → 9/17), geliştirme sürecinde hiç kullanılmamış iki yeni ders kitabında (Biyoloji 12 ve T.C. İnkılâp Tarihi ve Atatürkçülük 12) K42 ile aynı bağımsız kurul yöntemiyle ölçmek.
- **Ölçülen ürün kodu:** `ba44473` (ürün kodu dondurulmuştur)
- **Rastgelelik tohumu:** `20261116`
- **Kilitli havuz dosyası:** `veri/bagimsiz3/havuz.json` (git dışında tutulur, LF satır sonu)
- **SHA-256 parmak izi:** `db127255975e612b46d628368a944f850b79b300f043367459cd2a8908f68702`

---

## 1. Yeni Kitaplar

| Dosya | Kitap | PDF Sayfa | Metinli Sayfa | Blok Sayısı | SHA-256 (ilk 16) |
|---|---|---:|---:|---:|---|
| `veri/biyoloji12.pdf` | Biyoloji 12 | 213 | 210 | 6.206 | `1f0a78b8d035d330` |
| `veri/inkilap12.pdf` | T.C. İnkılâp Tarihi ve Atatürkçülük 12 | 287 | 281 | 5.108 | `64a392e28af85a93` |

---

## 2. Ölçüm Yöntemi

Yöntem K42 ile birebir aynıdır:
- **A (Sayfa okuma):** ChatGPT ve Gemini, belirlenen 30 adet A sayfasını baştan sona okuyarak sistemden bağımsız olarak yazım ve noktalama hatalarını çıkarır (`testseti/bagimsiz/A_talimat.txt` değiştirilmeden kullanılır).
- **Karar kurulu:** ChatGPT, Gemini ve DeepSeek'ten oluşan bağımsız kurul tüm adayları (A'dan gelenler ve B'den seçilen sistem tespitleri) oylar (`KURUL_talimat.txt` şablonu değiştirilmeden kullanılır).
  - Adaylar karışık sırada ve nötr kimliklerle (`K001`…) sunulur.
  - Adayın kaynağı, sistemin güven puanı veya önerisi kurula gösterilmez.
  - Karar çoğunluk oyuyla (en az 2/3 model) belirlenir.
  - Alıntı/replik/tarihî metinlerdeki yazar veya dönem üslubu hata sayılmaz (MEB TYMM 2.4.1); dizgi bozulmaları hata sayılır.
- **Metin katmanı mekanik kontrolü (K41-ek):** Bir adayın her sözcüğü sayfanın glif düzeyindeki karakterlerinde (`page.get_texttrace()`) aranır; bulunmayan sözcük varsa aday "metin katmanı farkı" olarak ayrılır, kurula gönderilmez, doğruluk pay ve paydasından çıkarılarak ayrı raporlanır.
- **Kimler etiket koymaz:** Claude (asistan) ve öğrenci etiketleme yapmaz; oylama sonuçları mekanik olarak toplanır.

---

## 3. Kilitli Örneklem ve Havuz

Ölçüm sayfaları `testseti/araclar/k45_havuz.py` ile `20261116` tohumu kullanılarak sistem çalıştırılmadan önce seçilmiş ve kilitlenmiştir:

### A Sayfaları (Bulma Oranı — 30 sayfa)
İlk ve son 10 sayfa hariç (`10 < sayfa_no < son - 10`), en az 150 kelime paragraf içeren uygun sayfalar arasından rastgele 15'er sayfa:
- **Biyoloji 12 (15 sayfa):** 17, 19, 71, 77, 78, 88, 111, 116, 127, 137, 164, 165, 169, 186, 190
- **T.C. İnkılâp Tarihi ve Atatürkçülük 12 (15 sayfa):** 23, 79, 87, 117, 130, 141, 150, 166, 178, 179, 182, 205, 224, 262, 273

### B Havuzu (İsabet — A dışındaki bütün sayfalar)
- İki kitabın A dışındaki **bütün** sayfalarında (Biyoloji 12: 198 sayfa, İnkılâp 12: 272 sayfa; toplam 470 sayfa) hakemli sistemin gösterdiği (`güven ≥ 0,5`) yazım tespitlerinin tamamı alınır; 80'den fazlaysa `20261116` tohumuyla rastgele 80 seçilir.
- Ayrıca K44'ün dokuz kuralının (`bitisik_rakam`, `yil_virgul_bosluk`, `liste_tutarsiz_virgul`, `iki_nokta_bosluk`, `yonerge_cift_nokta`, `yonerge_soru_isareti`, `bir_takim`, `birim_gr`, `yanlis_kelime`) ve `buyuk_harf_i`'nin bütün gösterilen tespitleri, 80'e girmeseler de eklenir (kural başına en çok 10; 10'dan fazlaysa `20261116:<alt_tur>` tohumuyla 10 seçilir).
- Hakemsiz sonuç ikincil olarak aynı yöntemle verilir (ortak tespitler kurula bir kez sunulur).

---

## 4. Başarı Ölçütleri ve Karşılaştırma Planı

Önceden sabitlenen ve sonradan değiştirilmeyecek başarı ölçütleri:
1. **Hakemli isabet ≥ %35.**
2. **Bulma oranı (gösterilen) ≥ %30.**
3. **Öncelik sırası ters değil:** `güven = 1,0` grubunun isabeti, `güven = 0,75` grubununkinden düşük değil (grup başına 5'ten az tespit varsa "ölçülemedi" yazılır).
4. **Kural bazında isabet:** K44 kurallarından en az 3 tespiti olan her birinin isabeti **≥ %50**; altında kalan kural sonuç belgesinde işaretlenir (bu görevde ürün değişikliği yapılmaz).

**Karşılaştırma:**
- Sonuç belgesinde K42 sonuçları (hakemli isabet 7/25 = %28,0, bulma oranı gösterilen 0/17 = %0,0) ve K44 geliştirme sonuçları (isabet 7/16 = %43,8, bulma oranı gösterilen 9/17 = %52,9) K45 sonuçlarıyla yan yana verilecektir.
- Yeni kitaplar farklı sınıf ve ders (özellikle TDE yerine İnkılâp Tarihi) olduğu için doğrudan karşılaştırmanın sınırları açıkça yazılacaktır.
