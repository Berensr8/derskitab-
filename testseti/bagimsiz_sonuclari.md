# Bağımsız değerlendirme: yazım (K39, 2026-11-09)

**Neden:** Yöntem incelemesi (docs/yontem_incelemesi_2026-11-09.md, bulgu 1 ve 3) iki eksik buldu:
- Bütün isabet etiketlerini sistemi yazan yapay zekâ (Claude) tek başına koymuştu.
- Gerçek, yani bilerek eklenmemiş hatalarda bulma oranı hiç ölçülmemişti.

Bu çalışma ikisini de ilk kez, sistemi yazandan bağımsız biçimde ölçüyor.

## Yöntem

- **Ölçülen sistem:** Bugünkü kod, yazım ve kesme kuralları, yapay zekâ hakemi kapalı (arayüzün varsayılanı). Sistemin çıktısı kurul karar vermeden önce hesaplandı ve parmak iziyle kilitlendi (`testseti/bagimsiz_kilit.txt`, commit 6b08451). Karşılaştırmadan önce parmak izleri yeniden kontrol edildi; aynı.
- **A, bulma oranı:**
  - Biyoloji 9, Biyoloji 11 ve TDE 10'dan 30 rastgele sayfa seçildi (tohum 20261109). Hiçbiri daha önce etiketlenmemişti ve her birinde en az 150 kelime paragraf vardı.
  - ChatGPT ve Gemini sayfaları baştan sona okuyup yazım ve noktalama hatalarını listeledi (`A_talimat.txt`). Sistemin çıktısını görmediler. İkisi toplam 62 aday buldu.
- **B, isabet:** Sistemin gösterdiği (güven ≥ 0,5) tespitlerden 40 tanesi rastgele seçildi: 5 kitaptan 8'er tane (Biyoloji 9, 11; TDE 10, 11, 12), daha önce etiketlenmemiş sayfalardan.
- **Karar kurulu:**
  - Üç yapay zekâ oyladı: ChatGPT, Gemini ve DeepSeek. Üçü üç ayrı firmanın modeli.
  - 102 aday (A'dan 62, B'den 40) karışık sırada verildi. Kimliklerden adayın kaynağı anlaşılmıyordu; öneri ve gerekçe de gösterilmedi (`KURUL_talimat.txt`).
  - Etiket çoğunluk oyuyla (en az 2/3) belirlendi.
  - Alıntı kuralı baştan konuldu: alıntıdaki yazar ya da dönem yazımı hata sayılmaz (MEB TYMM 2.4.1); dizgi kazası alıntının içinde de hatadır.
- **Kimler etiket koymadı:** Claude kurulda yoktu ve hiçbir etikete karar vermedi; adayları birleştirdi ve oyları saydı. Öğrenci de etiket koymadı.

## Sonuçlar

### 1. İsabet: sistemin gösterdiklerinin kaçı gerçek hata? (B)

| Ölçü | Sonuç (%95 Wilson aralığı) |
|---|---|
| Çoğunluk (≥ 2/3) | **8/40 = %20** (%10–35) |
| Oybirliği (3/3) | 4/40 = %10 (%4–23) |
| En az bir model "hata" dedi | 18/40 = %45 (%31–60) |
| Güven 1,0 ("öncelikli") | 7/23 = %30 (%16–51) |
| Güven 0,5 ("kontrol edilecek") | 1/17 = %6 (%1–27) |

- **Kitaba göre:**

  | Kitap | Gerçek hata |
  |---|---|
  | Biyoloji 9 | 2/8 |
  | Biyoloji 11 | 1/8 |
  | TDE 10 | 2/8 |
  | TDE 11 | 3/8 |
  | TDE 12 | 0/8 |

- **Gerçek hatalar:** avakado, "Postmen da", asitbaz, ggerçekleştiriniz, san’atın, ta’lik, fâyık, "parçasıdır.(...)".
- **Yanlış alarmların türleri:**
  - Bilimsel terimler: glikoprotein, inflamasyon, kondrin, filogenetik, pupilla, anabolik/katabolik.
  - Alıntılardaki eski ya da halk yazımı: rabbime, kimseneyi, didi, oynaşur, âbıhayat.
  - Doğru Türkçe kelimeler: bazılarınız, nelere, okudunuzsa, lobu, ırgada.
- **Önceki ölçümlerle karşılaştırma:** Claude'un etiketlediği görülmemiş kitaplarda hakemsiz isabet ~%4 (6/137) çıkmıştı. Bağımsız kurulun sonucu daha yüksek: %20. İkisi de "gösterilenlerin çoğu hata değil" diyor.

### 2. Bulma oranı: sayfalardaki gerçek hataların kaçını buldu? (A)

- Kurul 30 sayfada 23 yere "hata" dedi. Bunların 2'si görsellerin içinde yazılı; PDF'in metin katmanında yok, yani sistemin göremeyeceği yerde ("1. Ve 2. Soruları", "ASYANIN KANDİLLERİ").
- **Metindeki 21 hatanın sonucu:**

  | Durum | Sayı (%95 Wilson aralığı) | Hatalar |
  |---|---|---|
  | Sistem gösterdi | **6/21 = %29** (%14–50) | asiti, molekullerinin, gecirgen, gecişidir, yuksek, kayaIıklar |
  | Buldu ama düşük önceliğe indirip gizledi | 2 | "nefs" (alıntıda), "dışardan" |
  | Kaçırdı | 13 | aşağıda |

  Gizlenenler de sayılınca oran 8/21 = %38 (%21–59).

- **Düzeltme (K41-ek):** Kurulun metinde "hata" dediği 21 maddeden 4'ü (A01: TAHRIŞ EDICI, A48: DINLEME, A16: Anahtarı’’, A25: ”Yüce) basılı sayfada var olmayan metin katmanı farkıdır (`page.get_texttrace()` ve sayfa görüntüsü incelendiğinde basılı sayfada bunların doğru yazıldığı görülmüştür). Bu 4 sahte hata çıkarıldığında **gerçek basım hatası 17**'dir. Sistemin bulduğu gerçek basım hatası: **6/17 = %35,3** (%95 Wilson aralığı: %17,3–%58,7).

- **Kaçırılan 13 hata, türlerine göre:**
  - Büyük harf ya da İ/I karışması (4): TAHRIŞ EDICI, DINLEME, "Milli Edebiyat dönemi", "Türk Edebiyatı".
  - Noktalama ve tırnak (4): "kazanır. (Görsel 1.26).", ’’ ile kapanan tırnak, ters açılış tırnağı, tırnak içi cümle sonunda nokta eksikliği.
  - Millî'de düzeltme işareti eksikliği (1).
  - Kesme (1): "Balkan Savaşlarına".
  - Dizgi (1): "0 civar" (O harfi yerine sıfır).
  - Kelime (1): "secici".
  - Kişi eki uyumsuzluğu (1): "Zorlandığınız … kullandığım". Bu daha çok anlatım konusu.

  Kaçırılanların çoğu, sistemin bilerek denetlemediği türlerden: büyük harfli kelimeler ve aralık boşluğu dışındaki noktalama. Bu, yöntem incelemesinin 1. bulgusunu ölçümle doğruluyor.
- **Sistemin bulduğu 6 hatanın 5'i tek sayfada:** S09'daki bilgi kutusu (Biyoloji 9, PDF s.114). Basılı sayfada da "molekullerinin secici gecirgen" ve "yuksek" yazdığı görüntüden doğrulandı; PDF'in metin katmanından kaynaklanan bir bozulma değil.
- **İsabet bu sayfalarda da benzer:** Sistemin 30 sayfada gösterdiği 23 tespitin 7'si gerçek hata (%30; %16–51). Gerisi bilimsel terimler (dorsal, ventral, immün, lizozim, sölenter vb.) ve alıntılardaki eski yazım.

### 3. Kurulun kendi içindeki uyumu

- **İkili uyum:** ChatGPT–Gemini %83, ChatGPT–DeepSeek %61, Gemini–DeepSeek %62.
- **Üçünün de aynı oyu verdiği aday:** 54/102.
- **Fleiss κ:** 0,33. Zayıf ile orta arası.
- **Ayrışmanın ana kaynağı:** DeepSeek alıntı kuralını çoğunlukla uygulamadı; neredeyse her adaya "alıntı değil" dedi ve eski yazımları hata saydı. ChatGPT ise S09'daki hataları "PDF bozulması" saydı; basılı sayfa bunun yanlış olduğunu gösterdi.

## Sınırlılıklar

- Doğruluk zemini insan uzman değil, üç yapay zekâdan oluşan bir kurul. Kurulun da kaçırdığı hatalar sayılamadı; bu yüzden bulma oranı gerçek değerin üst sınırıdır.
- Örnek küçük (21 hata, 40 tespit) ve aralıklar geniş. Gerçek hatalar kümeli: 21'in 5'i tek sayfada.
- Kurul uyumu düşük. İsabet, oylama kuralına göre %10 ile %45 arasında değişiyor; raporlanan değer çoğunluk kuralıyla bulunan %20.
- Sistem çıktısı hesaplanırken başka bir ajanın henüz commit edilmemiş değişiklikleri çalışma ağacındaydı (sonradan 4730fe4 ile commit edildi: alıntıdaki kesme tespitleri ve güven/öncelik ayrımı). Bu ölçümdeki tespitlerin neredeyse hepsi kelime denetiminden ve bu değişiklik onları etkilemiyor, ama tam olarak aynı kod sürümü değil.
- TDE 10 sayfalarının çoğu alıntı metin; edebiyat kitaplarında "hata" tanımı alıntı kuralına bağlı.

## Dosyalar

- Ham cevaplar: `testseti/bagimsiz/A_chatgpt.txt`, `A_gemini.txt`, `KURUL_chatgpt.txt`, `KURUL_gemini.txt`, `KURUL_deepseek.txt`.
- Talimatlar: `testseti/bagimsiz/A_talimat.txt`, `KURUL_talimat.txt`.
- Anahtarlar:
  - `kurul_anahtar.json`: kimlik → aday eşlemesi.
  - `A_birlesik_anahtar.json`: hangi yapay zekânın bulduğu.
  - `B_anahtar.json`: sistemin türü ve güveni.
  - `A_sistem_gizli.json`: kilitli sistem çıktısı.
  - `kurul_sonuc.json`: oylar ve çoğunluk.
- Araçlar: `testseti/araclar/k39_*.py`. Bunlar `veri/bagimsiz/` ve `bagimsiz_degerlendirme/` klasörleriyle çalışır; o klasörler git dışında.
