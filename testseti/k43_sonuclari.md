# K43: Sayfayı Yerel Modele Okutma Denemesi — Sonuçlar (2026-11-15)

- **Ön kayıt belgesi:** `testseti/k43_on_kayit.md` (commit `5e6acad`, model çalıştırılmadan önce kilitlendi)
- **Deneme betikleri:** `testseti/araclar/k43_deneme.py`, `testseti/araclar/k43_say.py`
- **Model ve ayarlar:** `gemma4:12b-it-qat`, `temperature=0`, `num_ctx=4096`, `num_predict=1024`
- **Veri:** K42'deki 30 A sayfası (`bagimsiz_degerlendirme2/A_30_sayfa_metin.txt`, `S01`–`S30`) ve bağımsız kurulun çoğunluk oyuyla belirlediği 17 gerçek hata.

---

## 1. Ön Kayıt Ölçütüne Göre Karar: **KAPAT**

| Ölçüt / Metrik | Ön Kayıt Şartı (Devam) | Ön Kayıt Şartı (Kapat) | Gerçekleşen Sonuç |
|---|---|---|---|
| **Bulunan gerçek hata** | $\ge 9 / 17$ (%52,9+) | $\le 8 / 17$ | **6 / 17 (%35,3)** |
| **Sayfa başına ortalama aday** | $< 5,00$ aday/sayfa | — | **2,23 aday/sayfa** (toplam 67 aday) |
| **İsabet (gerçek / toplam aday)** | — | — | **6 / 67 (%9,0)** |
| **Sayfa başına ortalama süre** | — | — | **12,51 sn** (toplam 375,2 sn) |
| **300 sayfalık kitap tahmini** | — | — | **62,5 dakika (~1,04 saat)** |
| **Teknik hata (JSON / zaman aşımı)** | — | — | **0 / 30 sayfa** |

- **Karar:** Model 17 gerçek hatanın yalnız **6'sını** bulabildiği için ($\le 8/17$) ön kayıt kuralı gereği sonuç **Kapat**'tır. Sayfayı yerel modele baştan sona okutarak aday üretme yolu ürüne alınmayacaktır.
- **Önemli ek bulgu:** Modelin yakaladığı 6 hatanın **5'i** (`Form11`, `yazınız..`, `Yönerge :`, `11,12, 13`, `1947,1962`) zaten `docs/iyilestirme_plani_2026-11-11.md` Bölüm 3'teki küçük ve hızlı düzenli ifade (regex) kurallarının yakaladığı mekanik boşluk/noktalama hatalarıdır. Bu denemenin asıl hedefi olan "kuralla yakalanamayan 8 hata"dan (`Sözlü alarak`, `Kap atışı`, `akıllı termostatlar;`, `solunum hızı;`, `Commasie`, `Canis familaris`, `Canidea`, `’abesdir`) model yalnız **1 tanesini** (`Commasie`) bulabilmiş, diğer 7'sini kaçırmıştır.

---

## 2. Bulunan Gerçek Hatalar (6 / 17)

| No | Kurul Kimliği | Sayfa | Kitaptaki Gerçek Hata | Modelin `kitaptaki` Çıktısı | Modelin `onerilen` Çıktısı |
|---|---|---|---|---|---|
| `A02` | `K046` | S02 (Biyoloji 9, s.76) | `Form11` | `Form11, Form 12, Form 13, Form 14'ten` | `Form 11, Form 12, Form 13, Form 14'e` |
| `A04` | `K064` | S02 (Biyoloji 9, s.76) | `Commasie` | `Commasie (Komasi) mavisi G-250` | `Coomassie (Komasi) mavisi G-250` |
| `A05` | `K052` | S03 (Biyoloji 9, s.87) | `yazınız..` | `yazınız..` | `yazınız.` |
| `A08` | `K003` | S07 (Biyoloji 9, s.150) | `Yönerge :` | `Yönerge    :` | `Yönerge:` |
| `A09` | `K081` | S08 (Biyoloji 9, s.155) | `11,12, 13` | `11,12, 13 ve 14.` | `11, 12, 13 ve 14.` |
| `A79` | `K045` | S30 (TDE 10, s.292) | `1947,1962` | `1947,1962` | `1947, 1962` |

---

## 3. Kaçan Gerçek Hatalar (11 / 17)

| No | Kurul Kimliği | Sayfa | Kitaptaki Yazım | Doğrusu | Hata Türü |
|---|---|---|---|---|---|
| `A07` | `K077` | S06 (Biyoloji 9, s.142) | `coğrafik` | `coğrafi` | Yanlış türetim |
| `A10` | `K080` | S08 (Biyoloji 9, s.155) | `Canis familaris` | `Canis familiaris` | Latince tür adı dizgisi |
| `A11` | `K076` | S08 (Biyoloji 9, s.155) | `Canidea` | `Canidae` | Latince familya adı dizgisi |
| `A14` | `K058` | S18 (Biyoloji 11, s.158) | `akıllı termostatlar;` | `akıllı termostatlar` | Gereksiz noktalı virgül |
| `A15` | `K019` | S18 (Biyoloji 11, s.158) | `örnek veriniz?` | `örnek veriniz.` | Emir cümlesi sonunda soru işareti |
| `A17` | `K065` | S19 (Biyoloji 11, s.167) | `Kap atışı` | `Kalp atışı` | Bağlamda geçerli başka kelime (harf düşmesi) |
| `A18` | `K098` | S20 (Biyoloji 11, s.224) | `solunum hızı;` | `solunum hızı,` | Yanlış noktalı virgül |
| `A23` | `K118` | S21 (TDE 10, s.68) | `gr` | `g` | Kısaltma standardı |
| `A29` | `K092` | S24 (TDE 10, s.84) | `bir takım vasıflar` | `birtakım vasıflar` | Bitişik yazılması gereken belgisiz sıfat |
| `A36` | `K007` | S25 (TDE 10, s.106) | `’abesdir` | `abestir` | Alıntı içi dizgi |
| `A50` | `K074` | S27 (TDE 10, s.237) | `Sözlü alarak ifade ediniz.` | `Sözlü olarak ifade ediniz.` | Bağlamda geçerli başka kelime (harf hatası) |

---

## 4. Boş Adayların Dağılımı ve 10 Rastgele Örnek

Modelin ürettiği toplam 67 adayın **61'i** gerçek hatayla eşleşmemiştir:
- **4 aday:** K42 kurulunun `DEGIL` (hata değil / alıntı) dediği adaylarla aynıdır.
- **57 aday:** Kurul listesinde olmayan tamamen yeni adaylardır (çoğunlukla ham metindeki satır sonu tirelemeleri veya modelin "kontrol edildi, doğrudur" diyerek listeye eklediği maddelerdir).

### 10 Rastgele Boş Aday Örneği (`random.Random(20261115)`)

| # | Sayfa | Kategori | Modelin `kitaptaki` Çıktısı | Modelin `onerilen` Çıktısı | Modelin Gerekçesi |
|---|---|---|---|---|---|
| 1 | S08 (Biyoloji 9, s.155) | Tamamen yeni | `yer almakta-dır?` | `yer almaktadır?` | Metinde 'yer almakta-dır' şeklinde bir satır sonu bölünmesi görülmektedir. Eğer bu bir dizgi hatasıysa ve kelime bölünmeden yazılacaksa düzeltilmelidir. Ancak satır sonu kuralına uygunsa hata sayılmamıştır. |
| 2 | S21 (TDE 10, s.68) | Kurul DEGIL (`A24`) | `nâzırı` | `nâzırı` | Hata değildir (Eski metin alıntısı olduğu için korunmuştur). |
| 3 | S13 (Biyoloji 11, s.102) | Tamamen yeni | `hare-ketler` | `hareketler` | Satır sonu bölünmesi hatalıdır; 'hareket' kelimesi 'hare' ve 'ket' şeklinde bölünmez. |
| 4 | S19 (Biyoloji 11, s.167) | Tamamen yeni | `dü-` | `dü-` | Satır sonu bölünmesi kontrol edildi. 'düzenlenir' kelimesi 'dü-', 'zenlenir' şeklinde bölünmüş. Bu kullanım doğrudur. |
| 5 | S25 (TDE 10, s.106) | Tamamen yeni | `di-` | `di-` | Metin içerisinde 'di-ğer' şeklinde bir satır sonu bölünmesi (hiphenation) mevcut. Bu bir dizgi tercihidir ancak 'di-' kısmından sonraki 'ğer' kelimesi bir sonraki satırda devam etmektedir. |
| 6 | S20 (Biyoloji 11, s.224) | Tamamen yeni | `açıkla-` | `açıklayınız.` | Satır sonu bölünmesi (tireleme) hatalı yapılmıştır. Kelime 'açıklayınız' şeklinde bitmelidir; 'açıkla-' şeklinde bölünmesi dizgi hatasıdır. |
| 7 | S19 (Biyoloji 11, s.167) | Tamamen yeni | `hi-` | `hi-` | Satır sonu bölünmesi kontrol edildi. 'hipofiz' kelimesi 'hi-', 'pofiz' şeklinde bölünmüş. Bu kullanım doğrudur. |
| 8 | S26 (TDE 10, s.215) | Tamamen yeni | `düşün-` | `düşün-` | Dizgi hatası: Kelime satır sonunda bölünmüş ancak bir sonraki satırda 'dü' şeklinde devam etmiş. Kelimenin kökü 'düşündü' olduğu için bölünme noktası ve devamı uyumsuz görünmektedir. |
| 9 | S19 (Biyoloji 11, s.167) | Tamamen yeni | `hipotalamustan` | `hipotalamustan` | Metin içerisinde 'hipotalamus' kelimesi özel isim gibi değil, genel bir biyolojik terim olarak kullanılmıştır... Yazım hatası yoktur. |
| 10 | S06 (Biyoloji 9, s.142) | Tamamen yeni | `Akci­ğerlerine` | `Akciğerlerine` | Kelime ortasında gereksiz tire (satır sonu kesmesi hatası) bulunmaktadır. |

---

## 5. Sayfa Bazında Süre ve Aday Dağılımı

- **Model ilk yükleme / ısıtma süresi:** 13,22 sn
- **30 sayfa toplam okuma süresi:** 375,19 sn (6,25 dakika)
- **Sayfa başına ortalama süre:** 12,51 sn (en kısa: 1,23 sn [S15]; en uzun: 46,56 sn [S13])
- **300 sayfalık bir kitap için tahmini süre:** ~62,5 dakika (1,04 saat)
- **Ön kayıttan sapma:** Yoktur. Hiçbir sayfa 4000 karakter sınırını aşmadığı için (en uzun sayfa S07: 3629 karakter) tüm sayfalar tek parçada gönderilmiş, istemde veya JSON şemasında koşu sonrasında hiçbir değişiklik yapılmamıştır.
