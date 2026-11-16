# K48: Yerel modelle sayfa okumayı ürüne eklemek (yazım ve noktalama)

Arka plan: K47 taraması (`testseti/k47_sonuclari.md`, Claude doğruladı). `gemma4:12b-it-qat`, temiz blok metniyle,
K42 ve K45 A sayfalarındaki 44 gerçek hatanın 18'ini buldu (mekanik 19; biri "’abesdir" için kitaptaki = önerilen,
gerçek bulma değil). Bunların 11'ini mevcut sistem bulmuyordu; ikisi birlikte 44'ün 26'sını kapsıyor. Bedeli:
sayfa başına ~2,25 aday, ~15 sn.

Claude'un 135 adaydan 30'luk örneğe bakışı: eşleşmeyen adayların önemli kısmı mekanik olarak ayıklanabilir
(kitaptaki = önerilen; yalnız sayfa düzeninden gelen başlık/form satırları "Adı Difüzyon…" → "Adı: Difüzyon…";
satır sonu tiresi kalıntıları "yapısı-"; alıntı içindeki eski metin), bir kısmı ise kurulun görmediği gerçek hata
olabilir ("Semuul Ruben"). Aşağıdaki süzgeçler bu gözleme dayanır ve **bu görevde ayarlanmaz**; etkileri sonraki
bağımsız ölçümde (K49, yeni kitap) ölçülecek.

## Kurallar (değişmez)

- Komutları her zaman `D:\derskitabı\.venv\Scripts\python.exe` ile çalıştır.
- Hiçbir şey indirme. Kullanıcının uygulamalarını kapatma, sistem ayarlarını değiştirme. GPU meşgulse dur ve bildir.
- Commit: küçük, Türkçe, `git commit -F <dosya>`. PowerShell `Set-Content` kullanma. Her commit şu satırla biter:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push yapma.
- Mevcut testlerin hepsi geçmeli (şu an 281). Gerileme setinde 55/56 düşmemeli.
- **İstem, şema ve süzgeç eşikleri K47 ile aynı kalır**; geliştirme verisinde (K42/K45) daha iyi sonuç için
  ayarlama yapma. Ürün metinlerindeki ölçülmüş oranlara (`rapor.py` OLCULEN_BASARI) yeni sayı yazma; yalnız
  "sayfa okuma eklendi, etkisi henüz bağımsız ölçülmedi" notu ekle.

## Yapılacaklar

### 1. Yeni modül: `derskitabi/kriterler/sayfa_okuma.py`

- Girdi: kitabın blokları (ürünün kendi temiz blok metni), sayfa sayfa. Sayfa metni = o sayfanın blokları okuma
  sırasıyla (K47 Araç 3 ile aynı birleştirme). K43/K47 sistem istemi, soru şablonu ve JSON şeması aynen
  (`testseti/k43_on_kayit.md`), sıcaklık 0, `gemma4:12b-it-qat`, `yerel_model.sohbet()`.
- Önbellek: `veri/sayfa_okuma_onbellek.json` (anahtar: model + istem sürümü + sayfa metninin özeti). Aynı kitap
  ikinci kez çalıştırılınca model yeniden çağrılmaz.
- Model cevap veremezse (bozuk JSON, zaman aşımı) o sayfa atlanır, uyarı yazılır; çalışma durmaz.
- Her aday kitap metninde bulunmalı: adayın "kitaptaki" metni o sayfanın bloklarından birinde (boşluk farkı yok
  sayılarak) geçmiyorsa atılır (modelin uydurduğu metin). Bulunduğu blok, tespitin `blok_no`'su olur.

### 2. Süzgeçler (sabit, ayarlanmaz)

Aday şu durumlarda **atılır**:
1. "kitaptaki" ile "önerilen" boşluk, büyük/küçük harf ve kıvrık/düz kesme farkı yok sayıldığında aynı.
2. Fark yalnız iki nokta üst üste ve/veya satır sonu eklemekten ibaret (sayfa düzeninden gelen başlık ve form
   satırları: "Adı Difüzyon" → "Adı: Difüzyon").
3. "kitaptaki" satır sonu tiresiyle bitiyor ve önerilen yalnız tireyi kaldırıyor ya da kelimeyi tamamlıyor
   ("yapısı-" → "yapısı", "spektru-" → "spektrum-").
4. Aynı yer için mevcut sistemin (kural, morfoloji, kesme) zaten bir tespiti var: yeni tespit üretilmez; mevcut
   tespitin açıklamasına "sayfa okuma da işaretledi" notu eklenir (öncelik değiştirilmez).

Atılan her aday sebebiyle sayılır (`iz` / ilerleme çıktısı), raporlanır.

### 3. Tespit

- `kriter="yazim"`, `alt_tur="sayfa_okuma"`, güven **0,5** ("kontrol edilecek"; "öncelikli" değil).
- Alıntı/replik içindeyse (ürünün `dusuk_oncelik` ipuçlarından alıntı) güven 0,25.
- Açıklama: "Yerel dil modeli (gemma4) sayfayı okurken işaretledi: '<kitaptaki>' → '<önerilen>'. Gerekçe: …
  Bu öneri bir dil modelinden gelir; ölçülmüş isabeti henüz bilinmiyor."
- `pdf_notlari.py` KURAL_ADLARI, `arayuz/ozet.py` sade adlar, `rapor.py` tür adları güncellenir.

### 4. Ürüne bağlama

- Hat (`arayuz/hat.py`), demo ve inceleyici: yazım hakemiyle aynı yaklaşım. Yeni ayar `sayfa_okuma`
  (varsayılan: Ollama ve gemma4 hazırsa açık, değilse kapalı; `yazim_hakem.hakem_varsayilani` gibi).
- Arayüzde (sunucu ve sayfa) seçenek gösterilir, yanında süre uyarısı: "Kitap başına yaklaşık 1 saat ekler
  (300 sayfa)". İlerleme her 10 sayfada bir yazılır.
- Hakem sayfa okuma tespitlerine sorulmaz (model zaten kendisi önerdi).

### 5. Testler

Sahte model fonksiyonuyla (Ollama gerekmeden): süzgeçlerin her biri, kitapta geçmeyen adayın atılması, mevcut
tespitle çakışmada not eklenmesi, alıntıda 0,25, bozuk JSON'da sayfanın atlanması, önbellek.

### 6. Geliştirme kontrolü (yalnız bilgi)

`testseti/araclar/k48_kontrol.py`: K42 ve K45 A sayfalarında ürün hattının (sayfa okuma açık) 44 gerçek hatadan
kaçını gösterdiği, sayfa başına sayfa okuma tespiti, süzgeçlerin attığı aday sayıları (sebebe göre).
`testseti/k48_gelistirme.md`'ye yaz, başlığın altına kalın: "Geliştirme verisi; süzgeçler bu sayfalara bakılarak
yazıldı. Gerçek etki K49'da yeni kitapta ölçülecek."

## Raporda istenenler

1. Commit'ler.
2. Değişen dosyalar ve kısa açıklama.
3. Test sayısı ve sonucu; gerileme seti.
4. Geliştirme kontrolü tablosu (44'ten kaçı, sayfa başına tespit, süzgeç sayıları, süre).
5. Bu görevden sapma.
