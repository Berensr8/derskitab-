# K48 geliştirme kontrolü: sayfa okuma ürün hattında

**Geliştirme verisi; süzgeçler bu sayfalara bakılarak yazıldı. Gerçek etki K49'da yeni kitapta ölçülecek.**

Sayfalar: K42 ve K45 A sayfaları (60), kurulun HATA dediği 44 gerçek hata. Hat: yazım denetimi + kitap ipuçları + yazım hakemi + sayfa okuma (`gemma4:12b-it-qat`, istem sürümü `k43-k47-v1`).

## Sonuç

| Ölçü | Değer |
|---|---|
| Sayfa okuma kapalıyken gösterilen (güven ≥ 0,5) tespitlerle bulunan | 15 / 44 |
| Sayfa okuma açıkken bulunan | **22 / 44** |
| Sayfa okumanın eklediği (önceden bulunmayan) | 7 |
| Sayfa okuma tespitiyle eşleşen gerçek hata (toplam) | 7 |
| Sayfa okuma tespiti (güven ≥ 0,5) | 62 (sayfa başına 1.03) |
| Sayfa okuma tespiti, gerçek hatayla eşleşmeyen | 55 (sayfa başına 0.92) |
| Alıntı içinde güveni 0,25'e inen sayfa okuma tespiti | 1 |
| Modelden gelen aday | 135 |
| Okunan / atlanan sayfa | 60 / 0 |
| Önbellekten gelen sayfa | 60 |
| Süre (yalnız sayfa okuma adımı, önbellek hariç/dahil) | 2.1 sn (0.04 sn/sayfa; 300 sayfalık kitap için ~0 dk) |

## Süzgeçlerin attığı adaylar (sebebe göre)

| Sebep | Aday |
|---|---|
| kitap metninde geçmiyor (modelin uydurduğu metin) | 5 |
| kitaptaki = önerilen | 50 |
| yalnız iki nokta / satır sonu farkı (sayfa düzeni) | 10 |
| satır sonu tiresi kalıntısı | 4 |
| mevcut sistem zaten işaretlemiş (nota eklendi) | 3 |
| aynı sayfada aynı aday tekrarı | 0 |

## Sınıfa göre (sayfa okuma açık)

| Sınıf | Bulunan |
|---|---|
| noktalama | 6 / 13 |
| kelime | 7 / 9 |
| diger | 9 / 22 |

## Sayfa okumanın eklediği gerçek hatalar

- `K42_A04`: `Commasie` → `Coomassie`
- `K42_A11`: `Canidea` → `Canidae`
- `K42_A17`: `Kap atışı` → `Kalp atışı`
- `K45_A13`: `gece gündüz fotosentezi` → `gece gündüz, fotosentezi`
- `K45_A20`: `Yaprağının enine kesitinde` → `Yaprağın enine kesitinde`
- `K45_A29`: `işaretleyiz` → `işaretleyiniz`
- `K45_A64`: `COVİD-19` → `COVID-19`

## Hâlâ bulunamayanlar

`K42_A10`, `K42_A14`, `K42_A18`, `K42_A36`, `K42_A50`, `K45_A02`, `K45_A06`, `K45_A08`, `K45_A15`, `K45_A17`, `K45_A19`, `K45_A23`, `K45_A24`, `K45_A28`, `K45_A39`, `K45_A46`, `K45_A51`, `K45_A52`, `K45_A53`, `K45_A60`, `K45_A63`, `K45_A66`

## Kitap başına süre (sayfa okuma)

| Kitap | Süre |
|---|---|
| Biyoloji 9 | 0.6 sn |
| Biyoloji 11 | 0.3 sn |
| Türk Dili ve Edebiyatı 10 | 0.2 sn |
| Biyoloji 12 | 0.5 sn |
| T.C. İnkılâp Tarihi ve Atatürkçülük 12 | 0.5 sn |

> Not: süre önbellekten gelen sayfaları içermez; önbellek boşken yaklaşık 15 sn/sayfa (K47).
