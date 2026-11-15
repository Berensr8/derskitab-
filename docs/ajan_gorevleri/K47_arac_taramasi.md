# K47: Yeni araçların taraması (noktalama modeli, hunspell-tr, yerel modelle sayfa okuma)

Arka plan: `docs/arastirma_yeni_yollar_2026-11-15.md`. Üç bağımsız ölçümde bulma oranı çok düşük çıktı
(K42: 0/17, K45: 1/27). Kural eklemek genelleşmedi. Bu görev, kaçan hata sınıflarını genel olarak ele alabilecek
araçları **elimizdeki etiketli veride, ayar yapmadan** sınar ve denemeye değenleri ayırır.

Bu bir **tarama**dır, ürün ölçümü değildir: sayfalar daha önce görüldü. Geçen araç ürüne girerse etkisi sonra
yeni kitapta bağımsız kurulla ölçülecek.

## Kurallar (değişmez)

- Komutları her zaman `D:\derskitabı\.venv\Scripts\python.exe` ile çalıştır (PyMuPDF 1.28.2).
- **Ürün koduna (`derskitabi/`) dokunma.** Yeni kod yalnız `testseti/araclar/k47_*.py`. Ürünün fonksiyonlarını
  (blok okuma, alıntı ayırma, yazım denetimi) içe aktarıp kullanabilirsin.
- Hiçbir şey indirme. Gerekenler kullanıcı onayıyla indirildi:
  - Noktalama modeli: `modeller/ytu-ce-cosmos__turkish-base-bert-punctuation-correction/` (BERT, uncased,
    etiketler `config.json` içinde: `. , ? ! ; : - '` ve `non`; kullanım örneği klasördeki `README.md`)
  - Hunspell sözlüğü: `modeller/hunspell-tr/tr_TR.dic`, `tr_TR.aff`; okuyucu `spylls` (.venv'de kurulu):
    `from spylls.hunspell import Dictionary; Dictionary.from_files(r"...\modeller\hunspell-tr\tr_TR")`
  - Yerel modeller (Ollama, kurulu): `qwen3.5:9b`, `gemma4:12b-it-qat`
- GPU'yu aynı anda iki iş için kullanma (Ollama modelleri ile BERT'i sırayla çalıştır). GPU meşgulse dur ve bildir.
- Kullanıcının uygulamalarını kapatma, sistem ayarlarını değiştirme.
- Commit: küçük, Türkçe, `git commit -F <dosya>`. PowerShell `Set-Content` kullanma. Her commit şu satırla biter:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push yapma.
- Sayıları olduğu gibi yaz. Ölçüt tutmayan araç kapatılır; bu da bir sonuçtur.

## Veri

- **Sayfalar:** K42 A sayfaları (30, `bagimsiz_degerlendirme2/A_sayfa_listesi.json`) ve K45 A sayfaları (30,
  `bagimsiz_degerlendirme3/A_sayfa_listesi.json`): toplam 60 sayfa.
- **Doğru cevaplar:** kurulun HATA dediği A maddeleri: K42'de 17 (`veri/bagimsiz2/`), K45'te 27 (`veri/bagimsiz3/`);
  toplam **44 gerçek hata**. Kurulun DEGIL dediği A adayları "kurulun reddettiği" diye ayrıca sayılır.
- **Metin:** sayfaların metni ürünün kendi bloklarından (`veri/<kitap>_bloklar.json`, yumuşak tire temizlenmiş).
  `A_30_sayfa_metin.txt` dosyalarını **kullanma** (K43'te içindeki tireler 67 adayın 50'sini sahte yaptı).
- **Eşleşme kuralı (K43 ile aynı):** aracın işaret ettiği parça, aynı sayfadaki bir gerçek hatanın "kitaptaki"
  metnini içeriyorsa ya da tersi (boşluk, büyük/küçük harf ve kıvrık/düz kesme farkı yok sayılır). Betikle say.
- **Hata sınıfları (mekanik):** "kitaptaki" ile "önerilen" yalnız noktalama işaretlerinde (`, ; : ? ! .`) ve
  boşlukta ayrılıyorsa **noktalama sınıfı**; tek kelimelik ve ikisi de harf içeriyorsa **kelime sınıfı**; geri
  kalanı **diğer**. Sınıf listesini ön kayda yaz.
- **Mevcut sistemin kapsadığı:** 44 hatanın, bugünkü ürünün (`HEAD`, K46 dahil) gösterdiği tespitlerle (güven
  ≥ 0,5) eşleşenleri. Her araç için "mevcut sistemin bulmadığı ama aracın bulduğu" ayrıca sayılır.

## Adımlar

### 1. Ön kayıt (hiçbir aracı bu sayfalarda çalıştırmadan önce, ayrı commit)

`testseti/k47_on_kayit.md`: sınıf listesi, eşleşme kuralı, aşağıdaki yöntemler ve eşikler (tam metinleriyle),
karar ölçütleri. Commit et. Sonra çalıştır. Eşikler, istemler ve kurallar sonradan değiştirilmez; teknik hata
düzeltmesi raporda yazılır.

### 2. Araç 1: noktalama modeli

- Yalnız `paragraf` blokları; ürünün alıntı ayırması (`kriterler/alinti.py`) alıntı ya da replik dediği bloklar
  atlanır.
- Her cümle için: noktalama işaretleri çıkarılıp model README'sindeki ön işlemle küçük harfe çevrilir, her
  kelimenin son alt parçasındaki tahmin okunur ve kitabın gerçek noktalamasıyla karşılaştırılır:
  - **Eksik:** model `,` `;` `:` `?` tahmin ediyor (olasılık ≥ **0,95**), kitapta o kelimeden sonra işaret yok.
  - **Fazla:** kitapta kelimeden sonra `,` ya da `;` var, model `non` diyor (olasılık ≥ **0,95**).
  - Cümle sonu (son kelime) değerlendirilmez.
- Bilgi için 0,90 ve 0,99 eşiklerindeki sayılar da verilir; **karar 0,95'e göre**.
- **Geçme ölçütü:** noktalama sınıfındaki gerçek hataların **en az yarısı** bulunur **ve** gerçek hatayla
  eşleşmeyen işaret sayfa başına **1'den az**.

### 3. Araç 2: hunspell-tr (üçüncü sözlük)

İki kullanım ayrı sayılır:
- **(a) Yanlış alarm süzgeci:** K42 ve K45 B listelerindeki kurul etiketli `morfoloji` tespitleri
  (`veri/bagimsiz2/B_anahtar.json`, `veri/bagimsiz3/B_anahtar.json` + kurul sonuçları). Hunspell kelimeyi geçerli
  sayarsa tespit düşük önceliğe inerdi: kaç DEGIL iner, kaç HATA kaybolur. **Geçme ölçütü:** en çok 1 HATA kaybı
  ve DEGIL'lerin en az %30'u iner.
- **(b) Bulucu:** 60 sayfada Starlang ve Zemberek'in geçerli saydığı ama hunspell'in tanımadığı kelimeler.
  **Geçme ölçütü:** kelime sınıfındaki gerçek hatalardan en az 3'ünü yakalar **ve** sayfa başına 1'den az
  eşleşmeyen işaret.
- Bilgi için: hunspell'in öneri listesi gerçek hataların doğrusunu ilk 3'te veriyor mu (ürünün açıklamasına
  "önerilen yazım" eklenebilir mi).

### 4. Araç 3: yerel modelle sayfa okuma (temiz metinle)

- K43'ün sistem istemi, soru şablonu ve JSON şeması **aynen** (`testseti/k43_on_kayit.md`), sıcaklık 0.
- Sayfa metni: o sayfanın bloklarının metni, okuma sırasıyla, alıntı/replik blokları dahil (model alıntıyı
  kendisi ayırmalı; istem bunu söylüyor).
- İki model sırayla: `qwen3.5:9b` ve `gemma4:12b-it-qat`.
- **Geçme ölçütü (model başına):** 44 gerçek hatanın **en az 15'i** **ve** sayfa başına ortalama **3'ten az**
  aday; ayrıca mevcut sistemin bulmadığı en az 8 hata. Sayfa başına süre ve 300 sayfalık kitap için tahmin
  raporlanır.

### 5. Sonuç

`testseti/k47_sonuclari.md`:
- Her araç: ölçüt tablosu (geçti/geçmedi), bulduğu ve kaçırdığı gerçek hatalar, 10 rastgele eşleşmeyen işaret
  örneği (tohum `20261117`), süre.
- Birleşik tablo: mevcut sistem tek başına, mevcut sistem + geçen araçlar (44 hatadan kaçı).
- Sınırlamalar: sayfalar görülmüş; eşleşmeyen işaretlerin bir kısmı kurulun görmediği gerçek hatalar olabilir
  (bu yüzden ölçüt muhafazakâr).
Commit et.

## Raporda istenenler

1. Commit'ler.
2. Her aracın sonucu ve kararı (geçti / kapatıldı).
3. Birleşik tablo.
4. Ön kayıttan sapma ve teknik sorunlar.
