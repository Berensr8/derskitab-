# Yöntem incelemesi (derin, 2026-11-09)

**İncelenen:** Projenin ölçümleri, test setleri ve kullanıcıya gösterilen başarı/güven cümleleri (KARARLAR.md, testseti/*_sonuclari.md, testseti/araclar/, derskitabi/rapor.py OLCULEN_BASARI, derskitabi/arayuz/ozet.py GUVEN).
**Ölçü:** "MEB'e sunulacak ürün": bir öğretmen ya da editör sistemin kendi başarısı hakkında söylediklerine güvenebilir mi?
**Süreç:**
1. 8 ayrı uzman ajan konuya göre incelendi: yazım, çelişki, kesme ve model, okunabilirlik ve müfredat, istatistik, etiketleme, ürün cümleleri, literatür ve MEB ölçütleri.
2. Çıkan 17 taslak bulgu birleştirildi.
3. Her bulguyu bağımsız bir savunma ajanı savundu, ardından bulguyu çıkaran uzman bir kez cevap verdi.
4. Son olarak bağımsız bir hakem ajan her bulgu için tut / hafiflet / at kararı verdi.

Hiçbir dosya değiştirilmedi.

---

## Genel değerlendirme

Projenin yöntem disiplini lisans düzeyinin üstünde. Karar kuralları önceden yazılmış, sayısal eşikler sonuçlardan önce git'e girmiş, olumsuz sonuçlar dürüstçe kaydedilmiş (K30, K31, K33). Proje belgeleri sınırları da çoğunlukla açıkça söylüyor.

Asıl sorun şu: bu sınırlar kullanıcının gördüğü metinlere geçmemiş. Ekran ve Excel cümleleri ("56'nın 55'i", "%100", "10–12. sınıf", "%67", "Güven 1,00") yapay ya da geliştirme setlerinden gelen en iyi sayıları genel başarı gibi sunuyor.

En büyük engel iki tane:
- Bütün doğruluk zemini, sistemi geliştiren yapay zekânın tek başına koyduğu etiketlere dayanıyor.
- Gerçek (bilerek eklenmemiş) hatalarda geri çağırma hiç ölçülmedi.

**Güven:** yüksek. Tartışmalı olgular kaynakta doğrulandı.

**Kritik bulgu yok.** Başta kritik sayılan dört bulgu, savunmadan sonra "önemli" düzeyine indi.

---

## Önemli bulgular

### 1. "56 hatanın 55'i" yalnız sistemin baktığı yerlerde ölçüldü; gerçek hatalarda geri çağırma bilinmiyor
- **Konum:**
  - Hataları üreten betik: `testseti/araclar/k23_yazim_olustur.py` (satır 10-11, 106-109, 128, 133).
  - Kör nokta kanıtı: `KARARLAR.md` K32 (~591-595).
  - Denetim kodu: `derskitabi/kriterler/yazim.py` (satır 45 `BUYUK_HARF_DENETIMI = False`, 49, 192).
  - Kullanıcıya gösterilen metinler: `derskitabi/arayuz/ozet.py:28` ve `:198`, `derskitabi/rapor.py:54`.
- **Sorun:**
  - Eklenen hatalar yalnız sistemin denetlediği konum ve türlere konmuş: küçük harfli, ≥6 harfli, blok başı/sonu olmayan, kitapta hiç geçmeyen kelimeler.
  - Bu yüzden set, sistemin kör noktalarını göremiyor. K32'de satır başı kelimelerinin hiç denetlenmediği bulunup düzeltildi ("hazılayabilirsiniz"), ama sonuç "56/56 (değişmedi)" kaldı.
  - Etiketli gerçek hataların hepsi sistemin zaten bulduklarından seçildi. Hiçbir sayfa baştan sona insan tarafından taranmadı.
  - Büyük harfle başlayan kelimeler (cümle başları dahil) ve kitapta 3 kezden fazla geçen yanlış yazımlar kelime denetimine girmiyor. TDK kuralları ve kesme denetimi ise büyük harfe bakıyor.
- **Savunmadan kalan:**
  - Set yine de işe yarıyor: terim, alıntı ve hakem katmanlarının gerçek hatayı yutmadığını sınıyor. "etmeize" kaybı bu setle yakalandı.
  - Proje belgesi bu sınırı açıkça yazıyor (`testseti/yazim_sonuclari.md:15-16`). Ama ürün metni yazmıyor.
- **Neden önemli:** Editör, "bilerek eklenen 56 hatanın 55'ini buldu" cümlesini genel bir başarı gibi okur. Sayfanın gerisini daha az dikkatli okuyabilir.
- **Düzeltme:**
  - Ekran ve Excel cümlesine bir kapsam yan cümlesi eklenmeli. Örnek: "sistemin aradığı türden, bilerek eklenmiş hatalar; büyük harfle başlayan kelimeler ve kitapta sık tekrarlanan yanlışlar denetlenmez".
  - 2-3 sayfa baştan sona insan tarafından taranmalı ve gerçek geri çağırma ölçülmeli.
- **Güven:** yüksek

### 2. Çelişkide "bulduklarının hepsi gerçekten çelişkiydi" yalnız yapay sette geçerli
- **Konum:**
  - Kullanıcıya gösterilen metinler: `derskitabi/arayuz/ozet.py:34-35`, `derskitabi/rapor.py:66-67`.
  - Eskimiş cümle: `testseti/tutarlilik_sonuclari.md:16`.
  - Kararlar: `KARARLAR.md` K22 düzeltmesi (~391), K29 eki (~596), K35.
  - Ekrandaki sahte tespit: `veri/turkdili12_tutarlilik_tespitler.json`.
- **Sorun:**
  - %100 kesinlik, ayar yapılan iki kitaba (Sosyal 6, Biyoloji 10) eklenen 35 çelişkiden geliyor. Bu iki kitabın kendi yanlış alarmları geliştirme sırasında görülüp temizlenmişti.
  - Dışarıda tutulan iki kitap (TDE 11, TDE 12) ilk koşuda yanlış alarm verdi.
  - Bugün TDE 12'de ekranda kalan tek uyarı sahte: Âşık Veysel ile Orhan Veli'nin biyografileri karşılaştırılmış. Bu uyarı "%100" cümlesiyle aynı bölümde görünüyor.
  - Dört gerçek kitapta (8.511 cümle çifti) hiç gerçek çelişki bulunmadı.
  - Test çelişkilerini sistemi geliştiren taraf yazdı. Kilitli test, cümle listesini değiştiren 4 kod değişikliğinden sonra yeniden koşulmadı. 5 kitapta tutarlılık hiç çalıştırılmadı.
- **Savunmadan kalan:**
  - Sahte uyarıların hepsi düşük güvende ve "çelişiyor olabilir" diliyle gösteriliyor.
  - "Test çelişkileri kolay" iddiası çürütüldü: kitabın kendi bilgi tekrarları da aynı benzerlik bölgesinde.
- **Düzeltme:**
  - Ekrandaki cümle kitap başına yanlış alarmı söylemeli: 4 kitapta 0-1, ikisi ayar kitabı.
  - Düşük güvenli uyarıların sahte olabileceği yazılmalı.
  - `tutarlilik_sonuclari.md:16` güncellenmeli.
- **Güven:** yüksek

### 3. Bütün isabet sayıları tek etiketçiye, sistemi yazan yapay zekâya dayanıyor
- **Konum:**
  - Etiket betikleri: `testseti/araclar/k23_etiketle.py`, `k25_test_etiketle.py`, `k29_etiketle.py`, `k34_kesme.py`.
  - Notlar: `KARARLAR.md` K20 eki, K33, K34.
  - Kullanıcıya gösterilen metinler: `derskitabi/rapor.py:51` (yorum: "elle etiketlerle") ve `:53-74`.
- **Sorun:**
  - %27, 8/9 ve 31/46 gibi isabet sayılarının hepsini Claude tek başına etiketledi. İkinci etiketçi de uyum ölçümü (kappa) de yok.
  - Test setlerini ve etiket tanımlarını da aynı taraf yazdı.
  - Etiket tanımları ve sözel ölçütler git dışındaki KARARLAR.md'de duruyor; zaman damgası yok.
  - Üç sonuç belgesi (`kesme_sonuclari.md`, `faz2_sonuclari.md`, `yazim_modeli_sonuclari.md`) ve ürün metinleri etiketleyenin kim olduğunu söylemiyor.
- **Savunmadan kalan:**
  - Geri çağırma setleri (56 yazım, 35 çelişki) yargı etiketi değil, yapı gereği hesaplanıyor.
  - Bazı etiketler koddan önce git'e girmiş; bu bir körlük kanıtı.
- **Neden önemli:** Kesme işaretinin ürüne girme kararı tek etiketçinin gri alandaki yargılarına dayanıyor (Bulgu 6).
- **Düzeltme:**
  - Her kriterden 30-50 tespiti Beren ya da bir öğretmen, sistemin etiketini görmeden etiketlemeli. Uyum raporlanmalı.
  - Ürün metnine "etiketler: geliştirici (yapay zekâ)" yazılmalı.
- **Güven:** yüksek

### 4. Yazımda yanlış alarm oranı ekranda hafife alınıyor
- **Konum:**
  - Ekran metni: `derskitabi/arayuz/ozet.py:28-29`.
  - Hakemin varsayılan ayarı: `derskitabi/arayuz/sayfa.html:279`.
  - Excel metni: `derskitabi/rapor.py:56-57`.
  - Matematik 11'in geliştirme kitabı olduğu: `KARARLAR.md` K15.
- **Sorun:**
  - Ekran "işaretlenen kelimelerin bir kısmı" hata değil diyor. Gerçek oranlar şöyle:
    - Görülmemiş kitaplarda, varsayılan ayarda (hakem kapalı), gösterilen kelime tespitlerinin ~%96'sı hata değil (6/137 gerçek).
    - Hakem açıkken ~%85 hata değil (6/39 gerçek).
  - Excel'deki "%27" bir geliştirme kitabından (Matematik 11) geliyor.
  - İsabet kitap türüne göre çok değişiyor: Sosyal 6'da ~%69, edebiyat kitaplarında %0-4.
  - "TDK kuralları 9 tespitin 8'inde isabetli" sayısı geliştirme kitaplarından geliyor ve 7 belirsiz tespit paydadan çıkarılmış. Belirsizler dahil 8/16, görülmemiş kitaplarda 3/7.
- **Savunmadan kalan:**
  - %27, Matematik 11 için iyimser değil, ihtiyatlı.
  - Hakem kapalıyken ekran bunu söylüyor.
  - Ollama olmayan makinelerde hakemin varsayılan olarak kapalı olması savunulabilir.
- **Düzeltme:**
  - Ekran cümlesi: "görülmemiş kitaplarda işaretlenenlerin çoğu (yaklaşık %85-96) hata değil; edebiyat kitaplarında isabet en düşük".
  - Excel'de TDK satırı "8/16; görülmemiş kitaplarda 3/7" olmalı.
- **Güven:** yüksek

### 5. Güven puanları olasılık gibi gösteriliyor ama kalibre değil
- **Konum:**
  - Excel: `derskitabi/rapor.py:116` (her kritere öncelik veriyor) ve `:142` (`0.00` biçimi).
  - Notlu PDF: `derskitabi/pdf_notlari.py:51-58`.
  - İnceleme sayfası: `derskitabi/sablonlar/inceleyici.html` ("YAZIM HATASI (güven 1,0)").
- **Sorun:**
  - Yazımda "güven 1,0" tespitlerinin ~%56'sı sahte.
  - 0,75 ile 0,5 güven düzeyleri ayırt edilemiyor (4/19'a karşı 3/21).
  - Kriterler arasında sıra ters: "kontrol edilecek" kesme tespitleri (0,5), "öncelikli" kelime tespitlerinden (1,0) daha isabetli.
  - Excel, hata olmayan okunabilirlik ve müfredat satırlarına da "yüksek" öncelik veriyor. K36 bu düzeltmeyi yalnız ekrana yapmıştı.
- **Savunmadan kalan:** Ana ekran sayı değil sıra sözcükleri kullanıyor ve sıralama kendi içinde tutarlı. 0,25 düzeyi gerçekten "büyük ihtimalle hata değil" (~%1 isabet).
- **Düzeltme:**
  - Excel ve PDF'te sayı yerine sıra sözcüğü kullanılmalı.
  - "Öncelik bir sıralamadır, olasılık değildir" notu eklenmeli.
  - Okunabilirlik ve müfredata Excel'de de öncelik verilmemeli.
- **Güven:** yüksek

### 6. Kesme işaretinde "%67 gerçek hata" sayısının çoğu alıntılardan
- **Konum:**
  - Etiketler ve kaynaklar: `testseti/kesme_etiketler.json`, `veri/yazim_modeli/k34_kaynaklar.json`.
  - Denetim ve alıntı kodu: `derskitabi/kriterler/kesme.py:198-210`, `derskitabi/kriterler/alinti.py:300-306`.
  - Excel metni: `derskitabi/rapor.py:59-62`.
  - MEB TYMM kriterleri 2.4.1, s.15: https://ttkb.meb.gov.tr/meb_iys_dosyalar/2024_10/15183917_tymm_kriter_ve_aciklamalari.pdf
- **Sorun:**
  - Gerçek sayılan 31 tespitin ~21'i yazar, çeviri ya da nutuk metninde. Örnekler: Karagöz, Tanpınar, Molière, Orhun çevirisi.
  - MEB 2.4.1, yazarın üslubundan ya da dönemin yazımından gelen farkların "hata olarak nitelendirilip düzeltilmemesini" istiyor.
  - Kitabın kendi metninde isabet 10/18 ≈ %56. Örnek küçük; güven aralığının alt sınırı %50'nin altında.
  - Alıntıdaki tespitler de "(TDK) kesme eksik" diye gösteriliyor. Alıntı düşürmesi yalnız kelime tespitlerine uygulanıyor.
  - Yapay geri çağırma (%28) ürün metninde yok.
  - Eski metin sınırı tutarsız etiketlenmiş: "Paşa'ların" sahte sayılmış, "Bursamızda" ve "Türkler'e" gerçek.
- **Savunmadan kalan:** Alıntılar kapsam dışı sayılınca da oran 0,50-0,70 bandında kalıyor; kesmeyi ürüne alma kararı değişmiyor. Alıntıdaki TDK dışı yazımı yakalamak, MEB'in istediği dipnot kontrolü için de işe yarar.
- **Düzeltme:**
  - Alıntı bloğundaki kesme tespitinin açıklaması: "alıntı ise yazımı korunur; dipnot var mı kontrol edin".
  - Excel: "kitabın kendi metninde yaklaşık %56; eksik kesmelerin ancak dörtte birini bulur".
- **Güven:** yüksek

### 7. Ekran her zor paragrafa "10-12. sınıf düzeyinde" diyor
- **Konum:**
  - Ekran metni: `derskitabi/arayuz/ozet.py:134-143` (sade_aciklama) ve `:222-224`.
  - Sayaç: `derskitabi/arayuz/sayfa.html:496`.
  - README: `README.md:7`.
  - Ölçüm: `testseti/okunabilirlik_sonuclari.md:58-67`.
- **Sorun:**
  - Kayıtlı sonuçların hepsinde, 6. sınıf kitabı dahil, işaretli paragrafların %100'üne "Formüllere göre 10-12. sınıf düzeyinde okunuyor" yazılıyor. Bu yalnız Çetinkaya-Uzun formülünün etiketi; Bezirci-Yılmaz aynı paragraflara "akademik" diyor.
  - Projenin kendi ölçümü formüllerin sınıfı ayırt etmediğini gösterdi (AUC 0,38-0,55).
  - "En zor %10" kuralı her kitapta ~%9-10 işaret üretiyor. "Sadeleştirilebilecek" ve "belirgin biçimde zor" nitelemeleri doğrulanmadı.
  - Aynı sonucu daha önce yayımlamış Kalyoncu ve Memiş (2024, OMÜ) kaynak gösterilmemiş.
- **Savunmadan kalan:** Excel, notlu PDF ve "Ne kadar güvenilir?" kutusu sınırı söylüyor. Ama tespit açılınca ilk okunan cümle bu sınırın tersini söylüyor.
- **Düzeltme:**
  - Sınıf cümlesi kaldırılmalı.
  - Sayaç "kitabın en karmaşık %10'u: N paragraf" olmalı.
  - README'deki kriter adı "Dilsel karmaşıklık" olmalı.
  - Kalyoncu ve Memiş (2024) anılmalı: https://avesis.omu.edu.tr/yayin/918c6c81-e073-4444-9be3-fc623d851a3f
- **Güven:** yüksek

---

## Küçük bulgular

- **Müfredat (`derskitabi/kriterler/mufredat.py:49-50`, `derskitabi/arayuz/hat.py:125-126`, `testseti/mufredat_sonuclari.md:82`):**
  - Künye ve kaynakça sayfaları kavram aramasına dahil. Bu yüzden Sosyal 6'nın 5. öğrenme alanı için "tema yok" notu çıkmıyor. "Bütün temanın yokluğu yakalanıyor" sözü bu kitapta tutmuyor.
  - Çok kelimeli kavramlarda aynı-sayfa eşleşmesi gevşek ve Biyoloji 11 temiz doğrulamasından sonra eklendi (kuralsız sonuç 14/16).
  - Atlama mesajı TDE programını "yüklü" gösteriyor, ama TDE programı hiç eşleşmez.
- **Kapsam (`README.md:3-8`, `derskitabi/arayuz/ozet.py:18`):**
  - Ürün neyi denetlemediğini hiçbir yerde söylemiyor: bilginin dış kaynakla doğruluğu, anlatım bozukluğu, görsel/tablo/altyazı, kitabın tutarlı biçimde tekrarladığı yanlış.
  - README "üç kriter" diyor; sistemde dört kriter var.
  - "Yazım ve dil" adı yapılan işi aşıyor; "Yazım ve noktalama" daha doğru.
- **Notlu PDF (`derskitabi/pdf_notlari.py:279-288`, `derskitabi/arayuz/sayfa.html:541`):**
  - "Ekibe gönderilebilir" denen PDF'in özet notu yazımda "bulunmadı" diyebiliyor, ama denetlenmeyen türleri ve hakemin açık/kapalı olduğunu söylemiyor.
  - Arayüz kullanıcısına bir komut satırı seçeneği (`--dusuk-guven`) öneriyor.
- **"Kilitli" adlandırması (`derskitabi/rapor.py:54`):** Yazım seti 7 kez koşuldu ve bir kez kodu yönlendirdi ("etmeize"). Ona "kilitli test seti" değil, "gerileme seti" denmeli.
- **Eğitilmiş model (`testseti/yazim_modeli_sonuclari.md`):**
  - Ürüne almama kararı sağlam (E7 1/60).
  - Ama "3-4 kat iyi" ve "gerçekten öğrendi" ifadeleri dağılım içi ölçümlere (E1, E4) ve %66 kelime örtüşmeli bir değerlendirmeye (E3) dayanıyor.
  - "28.148 Vikipedi / 205.229 cümle" kayıt sayısı. Vikipedi iki kat ağırlıkla eklenmiş; tekil sayı ~14 bin.
- **Okunabilirlik belgeleri (`derskitabi/degerlendirme_okunabilirlik.py:41-42`, `testseti/okunabilirlik_sonuclari.md:67`):**
  - "Biyoloji 11 ve TDE 10-11 eski program (Ünite)" deniyor; bloklar Tema düzeninde. "Ünite" düzenindeki tek kitap TDE 12.
  - Ölçüm K32'den sonra yeniden yapılmadı.
  - Ana sonuç değişmiyor, hatta güçleniyor.

## Yazara sorular

- **Tutarlılıkta LLM'siz taban:** Dil modeli kullanmayan bir taban (aynı varlık + farklı sayı/tarih kuralı, ya da küçük bir Türkçe NLI modeli) neden denenmedi? Geri çağırmaya katkısı en çok 1-2 madde olurdu. Ama isabet ve maliyet karşılaştırması raporda tek cümleyle gerekçelendirilmeli.

---

## Savunmadan sonra düşen ya da daralan iddialar

- **"Test çelişkileri kolay":** Düştü. Kitabın kendi bilgi tekrarları da aynı benzerlik bölgesinde.
- **"Kesme kararı alıntı tanımına bağlı":** Düştü. Alıntılar kapsam dışı sayılınca karar aynı kalıyor.
- **"Kilitler ve eşikler git'te kanıtlanamıyor":** Büyük ölçüde düştü. K20, K25, K28, K29, K33 ve K34'ün sayısal eşikleri ve etiketleri sonuçtan önce commit edilmiş.
- **"Gerçek kitapta yanlış alarm ölçülmedi":** Düştü. Dört kitapta ölçüldü ve kayıtlı.
- **"MEB ölçütlerinin küçük bir kısmı karşılanıyor":** Eleştiri olarak düştü, çünkü ödev üç kriter istiyor.
- **"Taban karşılaştırması yok":** Yazım için düştü. Hunspell, Zemberek ve Starlang (K13) ile GECTurk (K33) karşılaştırmaları var.

## Sağlam bulunanlar

- Formül katsayıları (Ateşman, Çetinkaya-Uzun, Bezirci-Yılmaz) ve Türkçe hece sayımı kaynaklarla uyumlu.
- Kilitli JSON'ların SHA-256 değerleri kayıtlarla aynı; kilitten sonra içerik değişmemiş.
- Olumsuz kararlar sağlam ve dürüst raporlanmış: eğitilmiş model (K33), müfredatta öğrenme çıktısı kapsamı (K31), kavramsal okunabilirlik (K30).
- Hakemin gerçek hata kaybı 0/37 ve 0,25 güven düzeyi ölçümle tutarlı (~%1 isabet).
- Proje belgelerinde ham sayılar yeniden hesaplandı ve hepsi tuttu.

## Bu incelemenin sınırları

- Bazı yeniden hesaplar (sahte oranları, kalibrasyon kovaları) uzman ve savunma ajanlarınca yapıldı; hakem, iki tarafın uyuştuğu değerleri kabul etti.
- Git dışındaki KARARLAR.md ve GUNLUK.md'nin hangi tarihte yazıldığı doğrulanamıyor.
- Ürün çalıştırılıp ekran görülmedi; ifadeler kaynak koddan ve kayıtlı sonuç dosyalarından okundu.
