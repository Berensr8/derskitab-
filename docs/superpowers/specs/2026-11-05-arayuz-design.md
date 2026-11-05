# Arayüz tasarımı (2026-11-05)

## Amaç
`DEMO.bat` (konsolda soru-cevap) yerine herkesin kullanabileceği sade bir program: öğretmen ya da editör konsol görmeden bir kitabı inceletir, sonucu basit cümlelerle okur, isterse tek tek inceler. Bütün incelemeler kayıtlı kalır.

## Hedefler
- **Yeni inceleme:** 1 Kitap (PDF seç; sayfa sayısı ve kapaktaki sınıf hemen görünür) · 2 Nereler incelensin (bütün kitap / sayfa aralığı; kriterler ve tahmini süreleri; tutarlılık ~1 saat ve yerel model ister — model kapalıysa açıkça söylenir) · 3 Çıktı klasörü.
- **İlerleme:** adım adım ne yapıldığı, geçen süre, vazgeç düğmesi. Tarayıcı sekmesi kapansa da iş sürer.
- **Sonuç ekranı (en önemli kısım, kullanıcının isteği):** her kriter için basit cümlelerle özet ("Yazımda 43 olası hata var; 31'ine önce bakın"), birkaç örnek alıntı ve her örneğin yanında yerine götüren küçük bağlantı (sayfa sayfa inceleme sayfasında o sayfa açılır). Tek tek incelemek için ayrı, sakin bir liste ekranı: ilk bakışta ayrıntı göstermez, istenirse açılır (öncelik süzgeci, alıntı, açıklama, "sayfada göster").
- **Çıktılar:** sayfa sayfa inceleme (HTML), notlu PDF, Excel raporu, klasör — tek tıkla.
- **Geçmiş:** bütün incelemeler listelenir, eskisi açılabilir.

## Hedef dışı (şimdilik)
- Üye girişi (ileri seviye). Kayıtlarda kullanıcı alanı şimdiden tutulur ("yerel"), giriş eklenince bağlanır.
- İnternetten erişim, çok kullanıcılı sunucu.

## Olmaması gerekenler
- "Yapay zekâyla yapılmış" görünüm: mor/mavi gradyan, cam efekti, emoji ikon, her şey kart.
- İlk bakışta ayrıntı yağmuru.

## Görünüm (kullanıcı seçti: A — "Editörün masası")
Kâğıt rengi zemin, mürekkep siyahı yazı, tek vurgu rengi kırmızı kalem. Kart yok, ince çizgiler. Başlıklar tırnaklı yazı tipi (Cambria/Georgia — Windows'ta hazır, internet gerekmez), gövde Segoe UI. Düzelti formu gibi 1-2-3 adım.

## Claude'un kararları
- Bilgisayarda çalışan küçük Python sunucusu (yalnız standart kütüphane: yeni indirme yok), tarayıcıda açılır; `INCELE.bat` ile başlar. Dosya/klasör seçiminde Windows'un kendi penceresi (tkinter).
- İnceleme ayrı bir süreçte çalışır (vazgeçilince süreç durdurulur; çökme sunucuyu etkilemez). İlerleme `ilerleme.jsonl`, sonuç `ozet.json` olarak çıktı klasörüne yazılır.
- Analiz hattı demoyla aynı (aynı modüller ve dosyalar); kullanıcıya soru sormaz, seçenekleri formdan alır.
- Özet cümleleri Python'da kurulur (test edilebilir); sayfa bağlantısı inceleme sayfasına `#s=<PDF sayfa>` ile gider.
- Geçmiş: `incelemeler/gecmis/<id>.json` (git dışı).
