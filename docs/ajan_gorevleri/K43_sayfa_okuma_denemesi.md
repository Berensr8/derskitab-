# K43: Sayfayı yerel modele okutma denemesi (fizibilite)

Bu bir **deneme**, ürün değişikliği değil. Soru tek: yerel model (gemma4) bir ders kitabı sayfasını
okuyarak, sistemin kurallarla yakalayamadığı hataları önerebiliyor mu? Cevap "hayır" ise bu yol
kapatılır. Arka plan: `docs/iyilestirme_plani_2026-11-11.md` bölüm 4.

## Kurallar (değişmez)

- Komutları her zaman `D:\derskitabı\.venv\Scripts\python.exe` ile çalıştır (PyMuPDF 1.28.2).
- Ürün koduna (`derskitabi/`) dokunma. Yeni kod yalnız `testseti/araclar/k43_*.py`.
- Hiçbir şey indirme. gemma4 zaten kurulu. Ollama kapalıysa başlatabilirsin; kullanıcının
  uygulamalarını kapatma, sistem ayarlarını değiştirme.
- GPU meşgulse dur ve bildir (bu deneme CPU'da çok yavaş olur, CPU'ya geçme).
- Commit: küçük, Türkçe, `git commit -F <dosya>`. PowerShell `Set-Content` kullanma (BOM ekler).
  Her commit mesajı şu satırla biter: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- Push yapma.
- Sayıları raporda olduğu gibi yaz. Hedef tutmazsa da sonuç budur; yuvarlama, süsleme yok.

## Girdiler

- Sayfa metinleri: `bagimsiz_degerlendirme2/A_30_sayfa_metin.txt` (30 sayfa, `===== Sxx | ... =====` başlıklı)
- Sayfa listesi: `bagimsiz_degerlendirme2/A_sayfa_listesi.json`
- Doğru cevaplar: `veri/bagimsiz2/A_birlesik_anahtar.json` (adaylar), `veri/bagimsiz2/kurul_anahtar.json`
  (A numarası → K kimliği), `veri/bagimsiz2/kurul_sonuc.json` → `sonuc` (K kimliği → HATA/DEGIL).
  Kurulun HATA dediği 17 A maddesi "gerçek hata" listesidir.
- Model çağrısı: `derskitabi/yerel_model.py` içindeki `sohbet()` ve `yalniz_bu_model()`.
  Model: `gemma4:12b-it-qat`, sıcaklık 0.

## Adımlar

### 1. Ön kayıt (modeli çalıştırmadan önce, ayrı commit)

`testseti/k43_on_kayit.md` dosyasına şunları yaz ve commit et:

- Modele verilecek sistem istemi ve soru şablonunun **tam metni**.
- Eşleşme kuralı: modelin önerisi, aynı sayfadaki bir gerçek hatayla eşleşir sayılırsa ancak
  önerinin "kitaptaki" metni gerçek hatanın "kitaptaki" metnini içeriyorsa ya da tersi
  (boşluk ve büyük/küçük harf farkı yok sayılır). Eşleşmeleri elle değil betikle say.
- Başarı ölçütü:
  - **Devam:** 17 gerçek hatanın en az 9'unu öneriyor **ve** sayfa başına ortalama 5'ten az aday üretiyor.
  - **Kapat:** 17'nin 8'i veya azı.
  - Arada kalırsa (en az 9 ama sayfa başına 5+ aday) sonuç "belirsiz" yazılır.
- Not: bu 30 sayfa daha önce görüldü. Sonuç ürünün başarısı değil, yolun açık olup olmadığıdır.

İstem yazarken dikkat: istemi bu 17 hataya göre ayarlama (örnek olarak onları verme, türlerini
sıralama). Genel bir editör talimatı olsun: "Bu ders kitabı sayfasında yazım, noktalama, dizgi ve
yanlış kullanılmış kelime hatalarını bul. Eski metin alıntılarını, şiirleri ve ağız özelliklerini
hata sayma. Her hata için kitaptaki hâlini, önerini ve kısa gerekçeni ver. Emin değilsen yazma."
JSON çıktı şeması: `[{kitaptaki, onerilen, gerekce}]`.

### 2. Çalıştırma (tek koşu)

`testseti/araclar/k43_deneme.py`:
- 30 sayfanın her birini ayrı istekle modele ver. Uzun sayfaları bölme gerekirse paragraf sınırından böl.
- Her sayfa için süreyi ölç.
- Ham çıktıları `veri/k43/cikti.json` dosyasına kaydet (git dışında).
- **İstemi koşudan sonra değiştirme.** Yalnız teknik hata (JSON bozuk, zaman aşımı) düzeltilebilir;
  bu durumda düzeltmeyi raporda yaz.

### 3. Sayım

`testseti/araclar/k43_say.py`:
- Kaç gerçek hata bulundu (x/17) ve hangileri.
- Toplam aday, sayfa başına ortalama aday.
- Gerçek hatayla eşleşmeyen adayların kaçı kurulun DEGIL dediği adaylarla aynı, kaçı tamamen yeni.
- Sayfa başına ortalama süre ve 300 sayfalık bir kitap için tahmini süre.

### 4. Sonuç belgesi

`testseti/k43_sonuclari.md`: ön kayıt ölçütüne göre karar (Devam / Kapat / Belirsiz), tablo,
bulunan ve kaçan hatalar, 10 rastgele boş aday örneği, süreler. Commit et.

## Raporda istenenler

1. Commit'ler ve kısa açıklamaları.
2. x/17, sayfa başına aday, sayfa başına süre.
3. Ön kayıt ölçütüne göre karar.
4. Teknik sorun olduysa ne yaptığın.
5. Ön kayıttan herhangi bir sapma.
