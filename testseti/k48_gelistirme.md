# K48 geliştirme kontrolü: sayfa okuma ürün hattında

**Geliştirme verisi; süzgeçler bu sayfalara bakılarak yazıldı. Gerçek etki K49'da yeni kitapta ölçülecek.**

> Claude düzeltmesi (K48 doğrulaması): görev metnindeki süzgeç 1 boşluk ve büyük/küçük harf farkını da yok sayıyordu; bu yüzden 'Ksilem de' → 'Ksilemde', '1953’ te' → '1953’te', 'suv' → 'SUV' gibi gerçek öneriler 'kitaptaki = önerilen' diye atılıyordu (ilk çalıştırmada 22/44). Süzgeç 1 artık yalnız tırnak biçimini ve boşluk dizisi uzunluğunu yok sayar; süzgeç 2 yalnız iki nokta EKLEYEN öneriyi atar; süzgeç 3 satır sonunda bölünmüş kelimeyi ('hazır\nlanması') de kapsar. İstem, şema ve model değişmedi.

Sayfalar: K42 ve K45 A sayfaları (60), kurulun HATA dediği 44 gerçek hata. Hat: yazım denetimi + kitap ipuçları + yazım hakemi + sayfa okuma (`gemma4:12b-it-qat`, istem sürümü `k43-k47-v1`).

## Sonuç

| Ölçü | Değer |
|---|---|
| Sayfa okuma kapalıyken gösterilen (güven ≥ 0,5) tespitlerle bulunan | 15 / 44 |
| Sayfa okuma açıkken bulunan | **26 / 44** |
| Sayfa okumanın eklediği (önceden bulunmayan) | 11 |
| Sayfa okuma tespitiyle eşleşen gerçek hata (toplam) | 11 |
| Sayfa okuma tespiti (güven ≥ 0,5) | 73 (sayfa başına 1.22) |
| Sayfa okuma tespiti, gerçek hatayla eşleşmeyen | 62 (sayfa başına 1.03) |
| Alıntı içinde güveni 0,25'e inen sayfa okuma tespiti | 2 |
| Modelden gelen aday | 135 |
| Okunan / atlanan sayfa | 60 / 0 |
| Önbellekten gelen sayfa | 60 |
| Süre (yalnız sayfa okuma adımı, önbellek hariç/dahil) | 2.0 sn (0.03 sn/sayfa; 300 sayfalık kitap için ~0 dk) |

## Süzgeçlerin attığı adaylar (sebebe göre)

| Sebep | Aday |
|---|---|
| kitap metninde geçmiyor (modelin uydurduğu metin) | 5 |
| kitaptaki = önerilen | 33 |
| yalnız iki nokta / satır sonu farkı (sayfa düzeni) | 9 |
| satır sonu tiresi kalıntısı | 4 |
| mevcut sistem zaten işaretlemiş (nota eklendi) | 9 |
| aynı sayfada aynı aday tekrarı | 0 |

## Sınıfa göre (sayfa okuma açık)

| Sınıf | Bulunan |
|---|---|
| noktalama | 7 / 13 |
| kelime | 7 / 9 |
| diger | 12 / 22 |

## Sayfa okumanın eklediği gerçek hatalar

- `K42_A04`: `Commasie` → `Coomassie`
- `K42_A11`: `Canidea` → `Canidae`
- `K42_A17`: `Kap atışı` → `Kalp atışı`
- `K45_A13`: `gece gündüz fotosentezi` → `gece gündüz, fotosentezi`
- `K45_A17`: `Farklı yönleri` → `Farklı Yönleri`
- `K45_A20`: `Yaprağının enine kesitinde` → `Yaprağın enine kesitinde`
- `K45_A23`: `Ksilemdeki su ,` → `Ksilemdeki su,`
- `K45_A24`: `Ksilem de` → `Ksilemde`
- `K45_A29`: `işaretleyiz` → `işaretleyiniz`
- `K45_A63`: `suv modeli` → `SUV modeli`
- `K45_A64`: `COVİD-19` → `COVID-19`

## Hâlâ bulunamayanlar

`K42_A10`, `K42_A14`, `K42_A18`, `K42_A36`, `K42_A50`, `K45_A02`, `K45_A06`, `K45_A08`, `K45_A15`, `K45_A19`, `K45_A28`, `K45_A39`, `K45_A46`, `K45_A51`, `K45_A52`, `K45_A53`, `K45_A60`, `K45_A66`

## Kitap başına süre (sayfa okuma)

| Kitap | Süre |
|---|---|
| Biyoloji 9 | 0.6 sn |
| Biyoloji 11 | 0.3 sn |
| Türk Dili ve Edebiyatı 10 | 0.2 sn |
| Biyoloji 12 | 0.5 sn |
| T.C. İnkılâp Tarihi ve Atatürkçülük 12 | 0.4 sn |

> Not: süre önbellekten gelen sayfaları içermez; önbellek boşken yaklaşık 15 sn/sayfa (K47).
