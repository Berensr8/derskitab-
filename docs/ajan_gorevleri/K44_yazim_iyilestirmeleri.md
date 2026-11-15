# K44: Yazım ve kesme iyileştirmeleri (geliştirme)

Arka plan: `docs/iyilestirme_plani_2026-11-11.md` bölüm 1, 2, 3 ve 5. K43 sonucu (`testseti/k43_sonuclari.md`):
sayfa okuma yolu kapandı, kaçan hatalar için doğru yol küçük kurallar.

Bu görev **geliştirmedir, ölçüm değildir.** Gerçek etki sonraki görevde (K45) hiç görülmemiş kitaplarda,
bağımsız kurulla ölçülecek. Bu yüzden burada çıkan sayılar "geliştirme verisi (şişkin)" diye yazılır,
ürün metinlerine (`rapor.py` OLCULEN_BASARI, `arayuz/ozet.py` GUVEN) **yazılmaz**.

## Kurallar (değişmez)

- Komutları her zaman `D:\derskitabı\.venv\Scripts\python.exe` ile çalıştır (PyMuPDF 1.28.2).
- Yalnız mevcut 8 kitabı kullan (`veri/*_bloklar.json`, `veri/*.pdf`). Yeni kitap indirme, açma, okuma.
  K45 ölçümü yeni kitaplarda yapılacak; onları görmek ölçümü bozar.
- Kullanıcının uygulamalarını kapatma, sistem ayarlarını değiştirme. GPU meşgulse hakem için CPU'ya
  geçme, dur ve bildir.
- Commit: her bölüm ayrı, küçük, Türkçe, `git commit -F <dosya>`. PowerShell `Set-Content` kullanma.
  Her commit şu satırla biter: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- Push yapma.
- Mevcut testlerin hepsi geçmeli (`python -m unittest`, şu an 267). Bilerek eklenen 56 hatalık gerileme
  setinde 55 yakalama düşmemeli.
- Raporda sayıları olduğu gibi yaz. Bir kural beklenenden kötü çıkarsa ürüne alma ve sebebini yaz.

## Geliştirme verisi (kullanılabilir)

- K39: `testseti/bagimsiz/`, `testseti/araclar/k41_k39_olcum.py`
- K42: `veri/bagimsiz2/` (B_anahtar, A_birlesik_anahtar, kurul_anahtar, kurul_sonuc, *_sistem_hakemli/hakemsiz)
- 8 kitabın tamamı

## Bölüm 1. Eski metin sayfası ipucu

**Sorun.** K42'de hakemli sistemin 18 yanlış alarmının 9'u üç sayfadan geliyor; hepsi eski Türkçe ya da
halk ağzı: TDE 11 s.156 (6), TDE 10 s.19 (2), TDE 11 s.19 (1). 7 gerçek hatanın hiçbiri böyle bir sayfada değil.

**Alıntı ayırma (`kriterler/alinti.py`) neden kaçırdı** (bloklara bakılarak bulundu, doğrula):
- TDE 10 s.19: imzalı şiir ("Anonim (haz.: …)") iki sütun: solda eski metin, sağda günümüz Türkçesi.
  İmza sol sütunda; sağ sütun (x≈263) alıntı sayılmıyor. Yanlış alarmlar ("yoğruşur", "hoplaşır") sağ sütunda.
- TDE 11 s.19: Karagöz oyunu. Replik satırları ("HACİVAT — …") yakalanıyor, ama replikler arasındaki gazel
  dizeleri ("Beyâz üzre yazılmış…") replik değil.
- TDE 11 s.156: Orhun Abideleri atasözü tablosu. İmza yok, Farsça tamlama yok; eski dil işareti tutmuyor.

**Yapılacak.**
1. Önce `alinti.py`'de düzeltilebilenleri düzelt (imzalı alıntının yanındaki çeviri sütunu; replik
   sahnesindeki replik olmayan dize blokları). Genel olmalı, bu sayfalara özel olmamalı.
2. Ek olarak `kriterler/dusuk_oncelik.py`'ye yeni bir kitap ipucu ekle: **eski metin sayfası.** Bir sayfada
   (PDF parçası, terim ve alıntı ipuçlarından sonra kalan) en az 4 "iki araç da tanımadı" morfoloji tespiti
   varsa, o sayfadaki morfoloji ve kesme tespitleri düşük önceliğe (0,25) iner, açıklamaya not düşülür,
   `KITAP_IPUCU_NOTLARI`'na eklenir (raporda "eski metin sayfası" diye görünsün). Silinmez.
3. **İstisna:** kelime kitapta geçen geçerli bir kelimeye tek harf uzaklıktaysa (`yazim_hakem.yakin_dogru_kelime`
   ya da eşdeğeri) inmez. Sebep: K39'da Biyoloji 9 s.114'te tek sayfada 5 gerçek harf bozulması vardı
   ("molekullerinin", "gecirgen"). Bu tespitlerin görünür kaldığını doğrula.
4. Eşiği (4) yalnız yukarıdaki verilerle seç ve gerekçesini yaz; 8 kitapta kaç sayfanın bu ipucunu aldığını
   kitap kitap raporla (fen kitaplarında sıfıra yakın olmalı; değilse eşiği sorgula).

**Kabul.** K42'deki 9 yanlış alarm 0,25'e iner; K42'nin 7 gerçek hatası ve K39'un gerçek hataları ≥ 0,5'te kalır.

## Bölüm 2. Öncelik sırası

**Sorun.** K42'de güven 1,0 → 1/10, 0,75 → 1/8, 0,5 → 5/7. Güven 1,0 "iki araç da tanımadı" demek ve eski
kelimelerde iki araç da aynı yönde yanılıyor.

**Yeni sıra (yalnız morfoloji ve yeni kurallar; mevcut TDK kurallarının güvenine dokunma):**

| Güven | Ne |
|---|---|
| 1,0 | `buyuk_harf_i` (K42'de 3/3); hakem "doğru" dese de kitaptaki bir kelimeye tek harf uzak morfoloji (2/3) |
| 0,75 | İki araç da tanımadı (hakemsiz başlangıç değeri bu olur, 1,0 değil); hakem "hata" dedi; Bölüm 3'ün kuralları |
| 0,5 | Bugünkü 0,5'ler |
| 0,25 | Bugünkü gibi (gizli) |

Arayüzde "öncelikli" eşiği değişmeyecekse yeni sıranın arayüzde nasıl göründüğünü (`arayuz/ozet.py` `oncelik`)
kontrol et ve raporla.

**Kabul.** K42 B havuzu yeni sırayla yeniden sayılır (kurul kararları aynı, yalnız güvenler yeni):
güven grubu başına x/n tablosu, eski tabloyla yan yana. Sayılar çok küçük (grup başına 3–10); bunu yaz.

## Bölüm 3. Dokuz küçük kural

Hepsi `kriterler/yazim.py`'ye, kendi `alt_tur` adlarıyla. Güven 0,75 (aksi yazılmadıysa). Her biri için olumlu
ve olumsuz örnekli test yaz. Sayılar 8 kitabın tamamında Claude'un ön denemesinden; senin sayın farklı çıkarsa
yaz ve örnekleri listele.

| # | Kural | Doğru yakalama | Yakalamaması gereken | Ön denemede 8 kitapta |
|---|---|---|---|---|
| 1 | Büyük harfle başlayan kelime + bitişik rakam (`Form11`) | Form11, Form17, Tablo2 | Birim, kimyasal formül, büyük harf kısaltma (B12, CO2) | 3, 3'ü hata |
| 2 | İki yıl arasında boşluksuz virgül (`1947,1962`); iki sayı da 1000–2100 | 1947,1962 | Ondalık sayılar | 1 |
| 3 | Listede tutarsız virgül (`11,12, 13`): tam sayılar, ilk virgülden sonra boşluk yok, ikinciden sonra var | 11,12, 13 | Önünde % olan ondalıklar (`%14,8, 2040`) | 4 (1 hata, 3 yüzde) |
| 4 | İki noktadan önce boşluk (`Yönerge :`), **yalnız** kitap aynı kelimeyi en az 3 kez ve en az 3 katı sıklıkla boşluksuz yazıyorsa (kitap geneli sayım; `nispet_i_denetimi` gibi `kitap_bloklari` ile) | Yönerge : (3 boşluklu / 50 boşluksuz) | Sözlük maddeleri (`metabolizma : …`), form alanları (`Adı Soyadı :`) | 5 kelime |
| 5 | Çift nokta (`yazınız..`), yalnız son kelime yönerge emir kipi ise (bkz. 6'daki liste) | yazınız.. | Şiir ve konuşmalardaki ".." (TDE'de 17 örnek) | 2 fen kitabında |
| 6 | Yönerge emir kipinden sonra soru işareti (`örnek veriniz?`). Sabit liste: yazınız, veriniz, açıklayınız, belirtiniz, söyleyiniz, tartışınız, bulunuz, yapınız, cevaplayınız, gösteriniz, anlatınız, inceleyiniz, karşılaştırınız, değerlendiriniz, hazırlayınız, doldurunuz, yorumlayınız, sıralayınız, tamamlayınız | veriniz?, açıklayınız?, söyleyiniz? | "misiniz?", "musunuz?", "istediniz?" (genel -InIz eki kullanma) | 3, 3'ü hata |
| 7 | "bir takım" + sonraki iki kelimeden biri çoğul (-lar/-ler) | bir takım vasıflar, bir takım üstün değerler | bir takım oluşturunuz, bir takım sözcüsü | 7 (4 hata) |
| 8 | Sayıdan sonra "gr" (doğrusu "g") | 500 gr | "gram" ve harfle devam eden kelimeler | 2 |
| 9 | Küçük TDK listesi: coğrafik → coğrafi | coğrafik | — | 4 |

Not: "bir takım" ve benzeri ifadeler mevcut `BITISIK_AYRI` listesinde varsa çakışma yaratma; mevcut kuralı
yukarıdaki şartla daralt.

**Kabul.** 8 kitapta her kuralın tespit sayısı ve tam listesi raporda. K42 A sayfalarında hangi gerçek hataları
yakaladığı (ön denemede beklenen: Form11, 1947,1962, 11,12, 13, Yönerge :, yazınız.., örnek veriniz?, bir takım,
gr, coğrafik = 9/17).

## Bölüm 4. Kesme işareti

`kriterler/kesme.py` (K34 sahte tespitleri: eski metin 7, adı "-ce" ile biten kişi 4).
1. Bölüm 1'in eski metin sayfası ipucu kesme tespitlerine de uygulanıyor mu, kontrol et.
2. "-ce/-ça/-çe/-ca" ile biten kelime kitapta başka yerde özel ad olarak geçiyorsa ("Meryemce" kişi adı)
   dil adı sayma. Dil adlarını (Türkçe, Almanca, Arapça…) bozma; test yaz.
3. `testseti/kesme_etiketler.json` üzerinde önce/sonra: kaç sahte tespit düştü, kaç gerçek tespit kayboldu
   (gerçek kaybı 0 olmalı).

## Bölüm 5. Geliştirme ölçümü ve rapor

`testseti/araclar/k44_gelistirme.py` ile, hakem önbelleğini kullanarak (önbellekte olmayan yeni tespitler için
gemma4 çalışabilir):
- K42 B: hakemli isabet önce/sonra (önce: 7/25).
- K42 A: bulma oranı önce/sonra (önce: 0/17), hangi hatalar.
- K39: `k41_k39_olcum.py` ile önce/sonra.
- 8 kitapta toplam yazım tespiti sayısı önce/sonra, güven grubuna göre.

Sonuçları `testseti/k44_gelistirme_sonuclari.md`'ye yaz. Başlığın altına kalın harflerle: "Bu sayılar
geliştirme verisidir; kurallar bu hatalara bakılarak yazıldı. Gerçek etki K45'te ölçülecek."

## Raporda istenenler

1. Commit'ler ve kısa açıklamaları.
2. Bölüm başına: ne değişti, kabul ölçütü tuttu mu, tutmadıysa ne yaptın.
3. Geliştirme tablosu (önce/sonra).
4. Ürüne alınmayan kural varsa sebebi.
5. Test sayısı ve sonucu; gerileme seti sonucu.
6. Bu görevde yazılanlardan sapma.
