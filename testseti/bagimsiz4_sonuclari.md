# Bağımsız Değerlendirme 4 (K49) — Sonuçlar

- **Tarih:** 2026-11-24
- **Ön kayıt:** `testseti/k49_on_kayit.md` (commit `7cb5c89`, tohum `20261123`)
- **Kilit:** `testseti/bagimsiz4_kilit.txt` (sistem çıktısı `56faa1c`; A listesi ve kurul listesi `d3c40c5`, kurula
  gitmeden önce)
- **Ölçülen kod:** `68a7a71` (yazım hakemi ve sayfa okuma açık; ürünün varsayılanı)
- **Kitaplar:** Tarih 9 (264 s.) ve Coğrafya 9 (244 s.); projede hiç kullanılmamış dersler
- **Betikler:** `testseti/araclar/k49_*.py`; sayım `k49_oyla.py` → `veri/bagimsiz4/kurul_sonuc.json`
- **Kurul:** ChatGPT, Gemini, DeepSeek; 203 aday (A 68 + B 135), çoğunluk ≥ 2/3. Üç cevap da 203 kararın hepsini
  içeriyor. Fleiss κ = 0,375 (ikili uyum: ChatGPT–Gemini 0,85; ChatGPT–DeepSeek 0,59; Gemini–DeepSeek 0,64).

---

## 1. Ön kayıt ölçütleri

| # | Ölçüt | Sonuç | Tuttu mu? |
|---|---|---|---|
| 1 | Ürün isabeti (sayfa okuma dahil, katmanlı) ≥ %35 | **%24,8** | ✗ |
| 2 | Bulma oranı (sayfa okuma açık) ≥ %30 | **7/28 = %25,0** (%12,7–%43,4) | ✗ |
| 3 | Sayfa okuma katkısı ≥ 3 ve ≥ A hatalarının %10'u (2,8) | **+4** (kapalı 3/28 → açık 7/28) | ✓ |
| 4 | Sayfa okuma isabeti ≥ %30 | **14/60 = %23,3** (%14,4–%35,4) | ✗ |
| 5 | Öncelik ters değil (güven 1,0 ≥ 0,75) | 1,0: **6/21 = %28,6**; 0,75: **11/29 = %37,9** | ✗ |
| 6 | Kural başına ≥ %50 (B3'te ≥ 3 tespit) | `buyuk_harf_i` **0/7** ✗; `kesme_bosluk` **2/3** ✓; diğerleri < 3 tespit | kısmen |

**Önceden sabitlenen karar:** ölçüt 3 tuttu, ölçüt 4 tutmadı → **sayfa okuma varsayılanda kapatılır**, seçenek olarak
kalır; arayüzde ölçülen isabeti ve katkısı yazılır. Ürün metinleri K49 sayılarıyla güncellenir.

---

## 2. İsabet (B: sistemin gösterdiği uyarıların kaçı gerçek hata)

B havuzu: A dışındaki 478 sayfada gösterilen (güven ≥ 0,5) benzersiz tespitler.

| Katman | Nüfus | Örnek (kurulda) | Gerçek hata | İsabet (%95 Wilson) |
|---|---:|---:|---:|---|
| B1 — mevcut hat | N1 = 162 | 63 (17'si metin katmanı farkı, kurula gitmedi) | 18 | %28,6 (%18,9–%40,7) |
| B2 — sayfa okuma | N2 = 420 | 60 | 14 | %23,3 (%14,4–%35,4) |
| **Ürün (katmanlı)** | 582 | | | **%24,8** |

- Sayfa okuma 478 sayfada 420 uyarı gösterdi: **sayfa başına 0,88**. Ürünün gösterdiği uyarıların %72'si sayfa
  okumadan geliyor.
- **Metin katmanı farkı (20 B adayı, kurula gitmedi):** hepsi `buyuk_harf_i`. Coğrafya 9 s. 138–168'deki üst
  bilgide "SİSTEMLER" kelimesi basılı sayfada doğru (İ), PDF'in metin katmanında "I". Ön kayıt gereği pay ve
  paydadan çıkarıldı. Editör bunları ekranda yanlış alarm olarak görür; o gözle B1 isabeti 18/80 = %22,5, ürün
  isabeti **%23,1** olur (ana ölçü değil, duyarlılık).
- Kitaba göre: B1 Tarih 9 11/41, Coğrafya 9 7/22; B2 Tarih 9 7/30, Coğrafya 9 7/30.

### Türe göre (B1)

| Tür | Hata / kurulda |
|---|---|
| morfoloji (kelime denetimi) | 12 / 35 (1 belirsiz) |
| noktalama boşluğu | 4 / 6 |
| parantezden sonra nokta | 2 / 2 |
| `buyuk_harf_i` | 0 / 11 |
| gereksiz kesme | 0 / 4 |
| bitişik/ayrı ("hiç bir", alıntıda) | 0 / 2 |
| diğer (özel ad kesmesi, `bir_takim`, dizgi rakam-harf) | 0 / 3 |

### Güven grupları (B1) — öncelik yine ters

| Güven | Hata / kurulda |
|---|---|
| 1,0 | 6 / 21 (%28,6) |
| 0,75 | 11 / 29 (%37,9) |
| 0,5 | 1 / 13 (%7,7) |

1,0 grubunu `buyuk_harf_i` bozuyor: grubun 21 tespitinin 11'i bu kural ve hepsi "hata değil" (çoğunu kurul "PDF
bozulması" diye niteledi: "ETKINLIK", "LARI", "BILIMI", "KÖRFEZI"; tamamı büyük harfli başlıklar). `buyuk_harf_i`
dışında 1,0 grubu 6/10. Kural B3 örneğinde de 0/7; B1+B3 birlikte **0/18**, ayrıca 20 metin katmanı farkı.

### Kurallar (B3 ve B1 birlikte)

| Kural | B3 | B1+B3 |
|---|---|---|
| `buyuk_harf_i` | 0/7 | 0/18 (+20 katman farkı) |
| `kesme_bosluk` (K46) | 2/3 | 2/3 |
| `yonerge_cift_nokta` | 1/1 | 1/1 |
| `yonerge_soru_isareti` | 1/1 | 1/1 |
| `bir_takim` | — | 0/1 |

K44'ün diğer altı kuralı bu iki kitapta hiç tespit üretmedi.

### Sayfa okumanın yanlış alarmları (B2'de 46 "hata değil" ya da belirsiz)

- **PDF metin bozulması (13):** "Haz ar Deniz i", "Sur�ye", "olacaktr", "inanç̧", "23o 27ı", büyük-küçük karışık
  başlık; bir kısmını kurul "PDF" diye niteledi, bir kısmını DeepSeek hata saydı.
- **Tekrarlanan başlık ve sayfa öğeleri:** "Bu Ünitede Öğrenilecek Anahtar Kavramlar" (3 kez), "ÜNİTE ÜNİTE".
- **Doğru yazımı düzeltmeye çalışma:** "ham madde", "iş birlikli", "COVID-19", "alçalan", "tarihî bir önem".
- **Alıntıdaki dönem yazımı:** "Emevîler'in", "Hakana", "Kurultaya".

Gerçek hata bulduğu örnekler: "XIII. Yüzyılın", "Doç.Dr.", "taş levha üzerin yapılmış", "1.Ünite", "Öyleki",
"gerçekleştiriniz..", "metre/ saniye", "Kırıkale", "20 °C'un", "nüfusu artış hızını".

---

## 3. Bulma oranı (A: sayfalardaki gerçek hataların kaçını gösterdi)

- A adayı 68 (ChatGPT ve Gemini okumalarından; 14 dayanaksız ya da tekrar satır elendi). Kurul **28'ine HATA**
  dedi, 40'ına "hata değil" (24'ü alıntıdaki dönem yazımı: Tarih 9 s. 200 ve 213'teki uzun alıntılar), belirsiz 0.
- Bulunan (gösterilen tespitle mekanik eşleşme, K45 kuralı):

| Hâl | Bulunan |
|---|---|
| Sayfa okuma kapalı | 3 / 28 (%10,7) |
| **Sayfa okuma açık (ürün)** | **7 / 28 (%25,0)** |
| Gizli tespitler dahil | 8 / 28 |

- Sayfa okumanın eklediği 4 hata: "Mahkumların" (S08), "içersinde" (S13), "San Tiago" (S16), "Quebek" (S19).
  **Not:** "Mahkumların" eşleşmesi gevşek: sayfa okuma aynı cümleyi işaretledi ama düzeltme önerisi virgüle
  yönelikti, düzeltme işaretine değil. Öneriyi de şart koşan katı okumayla katkı **+3** (açık 6/28 = %21,4); ölçüt
  3 yine tutar (3 ≥ 3 ve ≥ 2,8). "içersinde" için öneri "içinde" (kurul "içerisinde" dedi); yer ve kelime doğru.
- Mevcut hattın bulduğu 3: "sürdürülüyor.Höyükteki", "aktardı.Çok" (noktalama boşluğu, 1,0) ve "techizatları"
  (morfoloji, 0,75). Gizlilerde ayrıca "vaka-i nüvist" (0,25, alıntı ipucu).
- **Kaçan 21 hatanın türleri:**
  - Düzeltme işareti eksikliği (halleriyle, liste halinde, resmi, mahkumların, askeri): 5. Kurulda ChatGPT
    bunlara "alıntı" dedi, Gemini ve DeepSeek hata.
  - Kelime hatası (özelikleri, mühime, vaka-i nüvist, itibariyle, Bogoto): 5.
  - Ay-yıl yazımında kısa çizgi (Kasım-2013 …): 3.
  - Özel ada gelen ekin kesmeyle ayrılmaması (Hasan Öğretmen'in, Avrupa Hun Devleti'yle): 2.
  - Tırnaktan sonra boşluk ("var.'Dedeoğlu"): 1.
  - Büyük harf (Neolitik ×2), virgül eksikliği, kurum adında kesme, grafik ekseni (1000): 5.

---

## 4. Karşılaştırma

| Ölçüm | İsabet | Bulma |
|---|---|---|
| K42 (Biyoloji 9/11, TDE 10) | 7/25 = %28 | 0/17 |
| K45 (Biyoloji 12, İnkılâp 12) | 20/76 = %26,3 | 1/27 = %3,7 |
| K48 geliştirme (şişkin, K42+K45 sayfaları) | — | 26/44 |
| **K49 (Tarih 9, Coğrafya 9)** | **%24,8** (mevcut hat %28,6; sayfa okuma %23,3) | **7/28 = %25,0** |

- Bulma oranı ilk kez anlamlı biçimde yükseldi (K45'te 1/27 → 7/28). Artışın yarısından fazlası sayfa okumadan
  (+4), kalanı mevcut hattın noktalama boşluğu kuralından geliyor. Geliştirmedeki %59 (26/44) yeni kitapta %25'e
  indi: süzgeçlerin geliştirme verisine uyumu yine görüldü.
- İsabet üç bağımsız ölçümde de %25–28 aralığında kaldı; K44/K46 değişiklikleri ve sayfa okuma isabeti
  yükseltmedi.
- Dersler ve sınıflar farklı (bu ölçümde ilk kez Tarih ve Coğrafya, 9. sınıf); Coğrafya 9'un PDF'inde büyük harfli
  başlıklarda metin katmanı I/İ sorunu yaygın. Doğrudan karşılaştırmanın sınırı budur.

---

## 5. Sınırlamalar

- Kurul uyumu orta (κ 0,375; K45'te 0,425). Ayrışma çoğunlukla alıntıdaki düzeltme işaretlerinde (ChatGPT
  "alıntı", diğerleri "hata") ve PDF bozulmalarında (DeepSeek çoğunlukla "hata").
- A hataları yalnız iki modelin okumasından geliyor; ikisinin de görmediği hatalar paydada yok (bulma oranı
  iyimser olabilir). Sayfa okumanın A sayfalarında bulup okuyucuların görmediği yerler ölçülmedi.
- Gemini'nin A ve kurul cevapları sütun ayraçları olmadan kopyalandı; A maddeleri elle, kurul kararları karar
  kalıbıyla ayrıştırıldı (203/203).
- Kullanıcının ayrıca kaydettiği DeepSeek A okuması (yalnız S01–S06, yarıda kesik) ön kayıtta olmadığı için
  kullanılmadı.
- Her kitapta bir sayfada model geçerli cevap vermedi (Tarih 9 s. 246, Coğrafya 9 s. 239); o sayfalarda sayfa
  okuma tespiti yok.

## 6. Sonraki işler (bu ölçümde ürün değişmedi)

1. **`buyuk_harf_i`:** tespiti, sayfanın glif katmanında (K41-ek kontrolü, `page.get_texttrace()`) da "I" varsa
   göster. Bu iki kitapta 18 gösterilen + 20 katman farkı tespitin hepsi yanlış alarm; 1,0 grubunu bozan tek
   etken.
2. **Sayfa okuma:** PDF metin bozulması (kitapta geçmeyen karakterler, kelime içi boşluk) ve sayfada tekrarlanan
   başlıklar için süzgeç; yeni ölçüm yeni kitap gerektirir.
3. **Kaçan türler:** özel ada gelen ekin kesmesiz yazılması ve ay-yıl arasındaki kısa çizgi kurala dönüştürülebilir.
