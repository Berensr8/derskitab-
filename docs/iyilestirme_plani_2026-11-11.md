# İyileştirme planı: her kısımda doğru yakalamayı artırmak (2026-11-11)

Bu belge bir "yapılacaklar" listesi değil, bir eleme listesidir. Her fikir yazılmadan önce eldeki
veride sınandı: kural kitaplarda kaç kez çalışıyor, bulduklarının kaçı gerçek, kurulun bulduğu
hataların kaçını yakalardı. Veride işe yaramayan fikirler elendi ve sebebiyle en sonda duruyor.

**Önemli uyarı.** Buradaki sayılar daha önce görülmüş sayfalardan çıkıyor (K39 ve K42 sayfaları ile
kitapların tamamı). Bunlar fikrin boş olmadığını gösterir, ürünün başarısını göstermez. Her adımın
gerçek etkisi ancak hiç kullanılmamış sayfalarda ölçülür ("Ölçüm" bölümü).

Sınamada kullanılan veri: 8 kitabın kayıtlı metni (`veri/*_bloklar.json`), K42 kurul kararları
(`veri/bagimsiz2/`), sonuç belgeleri (`testseti/*_sonuclari.md`).

## Özet

| # | Kısım | Yapılacak iş | Beklenen etki (görülmüş veride) | Maliyet | Karar |
|---|---|---|---|---|---|
| 1 | Yazım: isabet | Eski metin sayfalarındaki tespitleri düşük önceliğe almak | Hakemli isabet 7/25 → en çok 7/16 | Küçük | Yap |
| 2 | Yazım: isabet | Öncelik sırasını yeniden kurmak | "Öncelikli" grubu 1/10'dan kurtulur | Küçük | Yap |
| 3 | Yazım: bulma | 9 küçük dizgi ve noktalama kuralı | Kaçan 17 hatanın 9'u | Küçük | Yap |
| 4 | Yazım: bulma | Sayfayı yerel yapay zekâya okutmak | Kalan 8 hatanın tek yolu | Büyük | Önce küçük deneme |
| 5 | Kesme işareti | Eski metin ve "-ce" ile biten adlar | 15 sahte tespitin 11'i | Küçük | Yap |
| 6 | Bilgi tutarsızlığı | Önce bağımsız ölçüm | Gerçek oran bilinmiyor | Orta | Ölçmeden dokunma |
| 7 | Müfredat | Kavramı kendi temasında aramak | Belirsiz | Orta | Önce küçük deneme |
| 8 | Okunabilirlik | — | — | — | Yapma |

## 1. Yazım: isabeti artırmak

**Şimdiki durum.** Hakemli sistemin gösterdiği 25 tespitin 7'si gerçek hata (%28).

**Bulgu.** 18 yanlış alarmın 9'u yalnız üç sayfadan geliyor ve hepsi eski Türkçe ya da halk ağzı
metin alıntısı:

| Sayfa | O sayfadaki "çözümlenemeyen kelime" sayısı | Yanlış alarmlar |
|---|---|---|
| TDE 11 s.156 | 6 | tutsıkıngındevlet, budunuğ, yitü, törüsin, kılbirleşik, bolsar |
| TDE 10 s.19 | 4 | yoğruşur, hoplaşır |
| TDE 11 s.19 | 5 | üzre |

7 gerçek hatanın hepsi ise sayfasında tek başına duruyor (sayfada 0 ya da 1 çözümlenemeyen kelime).

**Öneri.** Bir sayfada 4 ya da daha çok çözümlenemeyen kelime varsa o sayfa büyük olasılıkla eski
metindir; oradaki kelime tespitleri düşük önceliğe (0,25) iner. Silinmez, editör isterse görür.
Bu, mevcut alıntı ayırmanın (`kriterler/alinti.py`: imza satırı, eski dil işaretleri, replik)
kaçırdığı alıntılar için ek bir yoldur; yazmadan önce bu 9 tespitin alıntı ayırmadan neden
kaçtığına bakılmalı (belki asıl düzeltme oradadır).

**Beklenen etki.** Bu 25 tespitte 9 yanlış alarm gizlenir, hiçbir gerçek hata gizlenmez: 7/16 (%44).

**Risk ve önlemi.** K39'da Biyoloji 9 s.114'te tek sayfada 5 gerçek hata vardı (toplu harf
bozulması: "molekullerinin", "gecirgen"). Kural bunları da gizlerdi. Önlem: kelime geçerli bir
kelimeye tek harf uzaklıktaysa ("molekullerinin" → "moleküllerinin") kural uygulanmaz. Bu istisnanın
eski metin kelimelerinin kaçını geri getirdiği yazmadan önce sayılmalı; 9 sayısı bu yüzden üst sınır.

## 2. Yazım: öncelik sırasını düzeltmek

**Şimdiki durum.** Sıra ters: "öncelikli" (güven 1,0) 1/10, güven 0,5 ise 5/7.

**Bulgu.** Güven 1,0 şu demek: iki sözlük aracı da kelimeyi tanımadı ve dil modeli "hata" dedi.
Eski Türkçe kelimelerde üçü de aynı yönde yanılıyor, çünkü hiçbiri kelimenin alıntıda olduğunu
bilmiyor. Gerçek hataları ayıran işaretler başka:

| İşaret | Bu işareti taşıyan tespitler | Gerçek hata |
|---|---|---|
| Büyük harfte I/İ kuralı | 3 | 3 |
| "Kitapta geçen bir kelimeye tek harf uzaklıkta" | 3 | 2 |
| Sayfada tek başına | 16 | 7 |
| Eski metin sayfasında | 9 | 0 |

**Öneri.** Önceliği araçların hemfikir olmasına göre değil bu işaretlere göre vermek: I/İ kuralı ve
"kitaptaki kelimeye yakın" olanlar üste, eski metin sayfasındakiler alta. Ayrıca dil modeline
kelimeyle birlikte "bu cümle bir alıntının içinde mi" bilgisini vermek.

**Sınır.** İşaret başına 3 örnek çok az. Sıra kurulurken sayılar değil mantık esas alınmalı ve yeni
sayfalarda ölçülmeli.

## 3. Yazım: bulma oranını artırmak (ucuz kurallar)

**Şimdiki durum.** Kurulun 30 sayfada bulduğu 17 gerçek hatanın hiçbirini sistem göstermedi.
Sebep basit: mevcut kurallar rakam içeren yerleri bilerek atlıyor, diğer türlere hiç bakmıyor.

Her aday kural 8 kitabın tamamında çalıştırıldı:

| Kural | Kaçan hata | 8 kitapta kaç kez çalıştı | Bakılan örneklerde durum | Karar |
|---|---|---|---|---|
| Harf ile rakam bitişik | Form11 | 3 | 3'ü de hata (Form11, Form17, Tablo2) | Yap |
| Yıl,yıl boşluksuz | 1947,1962 | 1 | Hata | Yap |
| Listede tutarsız virgül | 11,12, 13 | 4 | 1 hata, 3'ü yüzde ("%14,8, 2040") | Yap, yüzdeyi atla |
| İki noktadan önce boşluk, kitabın kendi yazımına aykırıysa | Yönerge : | 5 kelime | "Yönerge :" 3 kez, "Yönerge:" 50 kez | Yap |
| Çift nokta, alıntı dışında | yazınız.. | 19 (2'si fen kitabında) | Fen: 2 hata. Edebiyat: şiir ve konuşma | Yap, edebî metni atla |
| Emir cümlesinden sonra soru işareti | örnek veriniz? | 3 | 3'ü de hata | Yap |
| "bir takım" + çoğul isim | bir takım | 7 | 4 hata, 3'ü doğru ("bir takım oluşturunuz") | Yap, çoğul şartıyla |
| Sayıdan sonra "gr" | gr | 2 | 2'si de hata (doğrusu "g") | Yap |
| "coğrafik" (TDK: coğrafi) | coğrafik | 4 | 4'ü de aynı | Yap, küçük liste |

**Beklenen etki.** Bu kurallar K42'de kaçan 17 hatanın 9'unu yakalardı.

**Dürüst sınır.** Kurallar bu 17 hataya bakılarak yazıldı, yani 9/17 şişkin bir sayıdır; yeni
sayfalarda oran daha düşük çıkacaktır. Ayrıca bu hatalar seyrek: 8 kitabın tamamında toplam yaklaşık
25–30 tespit eder. Kazanç "çok hata bulmak" değil, "bu türleri hiç görmeyen sistemin artık görmesi".

**İki noktadan önce boşluk için not.** Düz kural işe yaramaz: 8 kitapta 475 kez geçiyor, çoğu
sözlük maddesi biçimi ("metabolizma : …") ve form alanı ("Adı Soyadı :"). Yalnız kitabın aynı
kelimeyi çoğunlukla boşluksuz yazdığı durumlar alınmalı.

## 4. Yazım: sayfayı yapay zekâya okutmak

**Bulgu.** Kalan 8 hata kuralla yakalanamaz:

- Kendi başına geçerli kelimeler: "Sözlü alarak" (olarak), "Kap atışı" (kalp atışı).
- Noktalama: "akıllı termostatlar;", "solunum hızı;".
- Yabancı adlar: "Commasie", "Canis familaris", "Canidea".
- Alıntı içi: "’abesdir".

Bunları kurul sayfayı okuyarak buldu. Aynı işi yerel model (Ollama) yapabilir: sayfayı okur, aday
önerir, mevcut kurallar ve hakem adayı doğrular.

**Risk.** Kurulun önerdiği 82 adayın yalnız 17'si gerçek hataydı (%21) ve onlar yerel modelden güçlü
modellerdi. Yerel model daha çok yanlış aday üretebilir; kitap başına süre de uzar.

**Öneri.** Tam yazmadan önce küçük deneme: K42'nin 30 sayfası yerel modele okutulur, 17 hatanın
kaçını önerdiği ve kaç boş aday ürettiği sayılır. Yarısından azını buluyorsa bu yol kapatılır.
Deneme GPU ister ve kapsamı büyütür; kararı Beren verir.

## 5. Kesme işareti

**Şimdiki durum.** İsabet %67 (31/46), kitabın kendi metninde yaklaşık %56. Bulma oranı %28.

**Bulgu.** 15 sahte tespitin dağılımı: eski metin aktarımı 7, adı "-ce" ile biten kişi 4
("Meryemce’nin" dil adı sanılıyor), "Ömerî" 3 (düzeltildi), PDF okuma 1.

**Öneri.**
- 1. bölümdeki eski metin sayfası işaretini burada da kullanmak (7 sahte tespit).
- "-ce/-ça" ile biten kelime kitapta özel ad olarak geçiyorsa dil adı saymamak (4 sahte tespit).

**Bulma oranına dokunmamak.** %28 bilerek seçilmiş bir temkin: kural yalnız kitabın başka yerde
kesmeyle yazdığı adlara bakıyor. Gevşetmek isabeti düşürür. Kaçanlar (çok kelimeli adlar, cins ad
okuması olanlar) için güvenilir bir yol şu an yok.

## 6. Bilgi tutarsızlığı

**Şimdiki durum.** Bilerek eklenen 35 çelişkinin 27'si bulundu (%77), yanlış alarm yok.

**Bulgu.** Bu sayı güvenilir değil: çelişkileri sistemi yazan taraf ekledi ve gerçek kitaplarda
şimdiye kadar hiç gerçek çelişki bulunmadı. Neyin kaçtığını bilmeden iyileştirme yapmak kör atış
olur. Yazım kısmında aynı şey yaşandı: kendi ölçümümüz iyi görünüyordu, bağımsız ölçüm 0/17 çıktı.

**Öneri.** Önce ölçüm, sonra iyileştirme. Çelişkileri kurul üyelerinden biri eklesin (sistemi
bilmeden), sistem bunları arasın. Sonuç yine %70 üstündeyse bu kısma dokunulmaz.

**Bilinen zayıf nokta.** Kaçan 8 çelişkinin 5'inde aday çift bulundu ama hakem model çelişki görmedi
("en/ilk" türü %57, sözel %67). Bağımsız ölçüm de bunu gösterirse düzeltilecek yer hakemin sorusudur.

## 7. Müfredat

**Şimdiki durum.** Yalnız kitapta hiç geçmeyen kavramı bulur. Bir tema kitaptan çıkarıldığında o
temaya özgü kavramların azı eksik görünür (Biyoloji 9'da 5/17, Biyoloji 10'da 2/8).

**Öneri.** Kavramı kitabın tamamında değil, ait olduğu temanın sayfalarında aramak.

**Risk.** Programdaki tema sırası ile kitabın ünite sayfalarını eşlemek gerekir; eşleme yanlışsa
kural boş alarm üretir. Önce tek kitapta (Biyoloji 9) eksik tema testini bu yöntemle tekrarlamak
yeter: 5/17 belirgin biçimde artmıyorsa bırakılır.

## 8. Okunabilirlik

Yapılacak iş yok. Formüller sınıf düzeyini ayırt etmiyor (K24) ve bu kısım hata bulmuyor, yalnız
"dil ağır olabilir" uyarısı veriyor. Buraya harcanan emek doğru yakalamayı artırmaz.

## Ölçüm

- K39 ve K42 sayfaları artık görüldü; bundan sonra geliştirme seti olarak kullanılır.
- Her adımın etkisi yeni, kilitli sayfalarda ölçülür. Kilitli havuzda kullanılmamış sayfa kaldıysa
  oradan alınır; yetmezse yeni kitap gerekir (indirme için önce onay).
- Yazım için en az 60 yeni sayfa önerilir. K42'de 30 sayfadan 17 gerçek hata çıktı ve güven aralığı
  çok geniş kaldı.
- Ölçüt ölçümden önce yazılır (ön kayıt), sonuç tutmasa da olduğu gibi raporlanır.

## Önerilen sıra

1. **Bölüm 1, 2, 3 ve 5 birlikte** (hepsi küçük, GPU istemez, aynı "eski metin sayfası" işaretini
   paylaşır). Sonra tek bir bağımsız ölçüm.
2. **Bölüm 4'ün küçük denemesi** (karar Beren'de).
3. **Bölüm 6'nın bağımsız ölçümü.**
4. **Bölüm 7'nin tek kitaplık denemesi**, zaman kalırsa.

## Elenen fikirler

| Fikir | Neden elendi |
|---|---|
| Latince adları kitabın kendi yazımıyla karşılaştırmak | Biyoloji 9'da yanlış yazım "familaris" 2 kez, doğrusu "familiaris" 1 kez geçiyor: kural doğru olanı hata sayardı. "Canidea" ve "Commasie"nin doğrusu kitapta hiç yok. Dış bir ad listesi gerekir. |
| İki noktadan önceki her boşluğu bildirmek | 475 tespit, neredeyse tamamı tasarım tercihi. |
| Virgülden önceki boşluğu bildirmek | 152 tespitin 143'ü matematik kitabındaki formül. |
| "hiç bir", "bir çok", "herşey" için yeni kural | Kural zaten var; bulunan 14 örneğin çoğu eski metin alıntısında. |
| Noktalı virgül kullanımını kuralla denetlemek | Anlama bağlı; kural yazılamaz (4. bölüme kalır). |
| Kesme kuralını gevşetip bulma oranını artırmak | İsabeti düşürür; mevcut %28 bilinçli tercih. |
| Okunabilirlik formüllerini iyileştirmek | Hata bulmayan bir kısım. |
