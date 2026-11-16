# K47: Yeni Araçların Taraması Sonuçları

- **Tarih:** 2026-11-16
- **Ön kayıt:** `testseti/k47_on_kayit.md` (`f5013d5` commit'i ile araçlar çalıştırılmadan önce kilitlendi)
- **Veri:** K42 (30 sayfa, 17 gerçek hata) + K45 (30 sayfa, 27 gerçek hata) = **60 A sayfası**, **44 gerçek hata** (`HATA`), **106 kurul reddi** (`DEGIL` / `BELIRSIZ`).
- **Metin kaynağı:** `veri/<kitap>_bloklar.json` (ürünün yumuşak tireleri temizlenmiş kendi blokları; `A_30_sayfa_metin.txt` kullanılmadı).
- **Mevcut sistem (`HEAD`, `ce96bf8`):** 60 sayfada güven $\ge 0,5$ ile gösterilen tespitler 44 gerçek hatanın **15'ini (%34,1)** yakalıyor (`noktalama`: 5/13, `kelime`: 3/9, `diger`: 7/22).

## 1. Özet Karar Tablosu

| Araç | Alt Görev / Model | Ana Ölçütler | Sonuç | Süre (60 sayfa) | Karar |
|---|---|---|---|---|---|
| **Araç 1** | `ytu-ce-cosmos/turkish-base-bert-punctuation-correction` (eşik 0,95) | Noktalama $\ge 7/13$ **ve** eşleşmeyen $< 1,0$/sayfa | Noktalama **4/13**, eşleşmeyen **4,87/sayfa** (292 adet) | 9.93 sn (0,17 sn/sayfa) | **Kapatıldı** ✗ |
| **Araç 2 (a)** | `hunspell-tr` — Yanlış alarm süzgeci (B `morfoloji`) | `HATA` kaybı $\le 1$ **ve** `DEGIL` inen $\ge \%30$ | Hakemli B: kayıp **1/13**, inen **11/66 (\%16,7)**; Birleşik B: kayıp **1/18**, inen **15/124 (\%12,1)** | < 1 sn | **Kapatıldı** ✗ |
| **Araç 2 (b)** | `hunspell-tr` — Bulucu (Starlang+Zemberek geçerli, Hunspell red) | Kelime sınıfı $\ge 3/9$ **ve** eşleşmeyen $< 1,0$/sayfa | Kelime **1/9**, eşleşmeyen **0,37/sayfa** (22 adet; hamda 1,65/sayfa) | 29.5 sn | **Kapatıldı** ✗ |
| **Araç 3 (Qwen)** | `qwen3.5:9b` (temiz blok metniyle sayfa okuma) | Bulunan $\ge 15/44$, ek $\ge 8$, aday $< 3,0$/sayfa | Bulunan **12/44**, ek **6**, aday **2,93/sayfa** (176 aday; 23 sayfada JSON hatası) | 1078.54 sn (17,98 sn/sayfa) | **Kapatıldı** ✗ |
| **Araç 3 (Gemma)** | `gemma4:12b-it-qat` (temiz blok metniyle sayfa okuma) | Bulunan $\ge 15/44$, ek $\ge 8$, aday $< 3,0$/sayfa | Bulunan **19/44** (sıkı: 18/44), ek **12** (sıkı: 11), aday **2,25/sayfa** (135 aday) | 912.31 sn (15,21 sn/sayfa) | **Geçti** ✓ |

---

## 2. Araç 1: Noktalama Modeli (`ytu-ce-cosmos/turkish-base-bert-punctuation-correction`)

### 2.1. Ölçüt ve Eşik Tablosu

- **Süre:** 60 sayfa toplam **9,93 sn** (sayfa başına **0,166 sn**, 300 sayfalık kitap için **~0,83 dk**).

| Eşik | Noktalama Sınıfı (Ölçüt: $\ge 7/13$) | Toplam Bulunan (/44) | Mevcut Sistemin Bulmadığı (Ek) | Toplam İşaret | Eşleşmeyen İşaret (Ölçüt: $< 60$, yani $< 1,0$/sayfa) | Kurul Reddiyle Eşleşen | Karar |
|---|---|---|---|---|---|---|---|
| 0.90 | 4/13 | 5/44 | 5 | 323 (5.38/s) | 318 (**5.30/s**) | 7 | **Kapatıldı** |
| **0.95 (Ana)** | 4/13 | 5/44 | 5 | 297 (4.95/s) | 292 (**4.87/s**) | 6 | **Kapatıldı** |
| 0.99 | 4/13 | 4/44 | 4 | 245 (4.08/s) | 241 (**4.02/s**) | 5 | **Kapatıldı** |

### 2.2. Bulduğu ve Kaçırdığı Gerçek Hatalar (Eşik 0,95)

**Bulunan gerçek hatalar (5/44 — 4 `noktalama`, 1 mekanik bağlam eşleşmesiyle `kelime`):**
- `K42_A04` (`K42_S02`, `kelime`): kitaptaki `Commasie` $\rightarrow$ doğrusu `Coomassie` | Modelin işaret ettiği: `Proteinler Commasie` $\rightarrow$ `Proteinler: Commasie` (Eksik ':' (p=0.954)) *(Not: iki kelimelik bağlam parçası `Commasie` kelimesini içerdiği için mekanik eşleşti)*
- `K45_A02` (`K45_S01`, `noktalama`): kitaptaki `(Görsel 1.2)],1869` $\rightarrow$ doğrusu `(Görsel 1.2)], 1869` | Modelin işaret ettiği: `2)],1869` $\rightarrow$ `2 1869` (Fazla ',' -> non (p=1.000))
- `K45_A13` (`K45_S07`, `noktalama`): kitaptaki `gece gündüz fotosentezi` $\rightarrow$ doğrusu `gece gündüz, fotosentezi` | Modelin işaret ettiği: `gündüz fotosentezi` $\rightarrow$ `gündüz, fotosentezi` (Eksik ',' (p=1.000))
- `K45_A19` (`K45_S10`, `noktalama`): kitaptaki `Kloroplast içermez bu yüzden` $\rightarrow$ doğrusu `Kloroplast içermez, bu yüzden` | Modelin işaret ettiği: `içermez bu` $\rightarrow$ `içermez, bu` (Eksik ',' (p=1.000))
- `K45_A46` (`K45_S20`, `noktalama`): kitaptaki `riya tembellik` $\rightarrow$ doğrusu `riya, tembellik` | Modelin işaret ettiği: `riya tembellik` $\rightarrow$ `riya, tembellik` (Eksik ',' (p=1.000))

**Kaçırılan `noktalama` sınıfı gerçek hatalar (9/13):**
- `K42_A05` (`K42_S03`): `yazınız..` $\rightarrow$ `yazınız.`
- `K42_A08` (`K42_S07`): `Yönerge :` $\rightarrow$ `Yönerge:`
- `K42_A09` (`K42_S08`): `11,12, 13` $\rightarrow$ `11, 12, 13`
- `K42_A14` (`K42_S18`): `akıllı termostatlar;` $\rightarrow$ `akıllı termostatlar`
- `K42_A15` (`K42_S18`): `örnek veriniz?` $\rightarrow$ `örnek veriniz.`
- `K42_A18` (`K42_S20`): `solunum hızı;` $\rightarrow$ `solunum hızı,`
- `K42_A79` (`K42_S30`): `1947,1962` $\rightarrow$ `1947, 1962`
- `K45_A23` (`K45_S12`): `Ksilemdeki su ,` $\rightarrow$ `Ksilemdeki su,`
- `K45_A39` (`K45_S20`): `Kazım Karabekir;` $\rightarrow$ `Kazım Karabekir`

*(Not: `yazınız..`, `Yönerge :`, `11,12, 13`, `1947,1962`, `Ksilemdeki su ,` gibi dizgi/boşluk noktalamaları model ön işlemde noktalama işaretlerini soyduğu için yapısal olarak bu modelin kapsamı dışındadır; noktalı virgülün virgüle dönüşmesi gereken `K42_A14`, `K42_A18`, `K45_A39` maddelerinde ise model `non` yerine farklı noktalama olasılıkları dağıttığı için 0,95 eşiğini geçememiştir.)*

### 2.3. 10 Rastgele Eşleşmeyen İşaret Örneği (Eşik 0,95, Tohum `20261117`)

| # | Sayfa | Kitaptaki Parça | Model Önerisi | Gerekçe |
|---|---|---|---|---|
| 1 | `K42_S17` | `denge; vücut` | `denge vücut` | Fazla ';' -> non (p=0.969) |
| 2 | `K42_S02` | `Süre 80` | `Süre: 80` | Eksik ':' (p=1.000) |
| 3 | `K42_S28` | `edebiyatı; makale` | `edebiyatı makale` | Fazla ';' -> non (p=1.000) |
| 4 | `K42_S25` | `İpekten, Eski` | `İpekten Eski` | Fazla ',' -> non (p=1.000) |
| 5 | `K42_S26` | `da, Bir` | `da Bir` | Fazla ',' -> non (p=1.000) |
| 6 | `K45_S08` | `kaynağı Fe2` | `kaynağı: Fe2` | Eksik ':' (p=0.997) |
| 7 | `K45_S05` | `Ruben), 1941` | `Ruben 1941` | Fazla ',' -> non (p=0.996) |
| 8 | `K45_S08` | `Fe2+, NO2` | `Fe2 NO2` | Fazla ',' -> non (p=1.000) |
| 9 | `K45_S20` | `halkı, sarf` | `halkı sarf` | Fazla ',' -> non (p=1.000) |
| 10 | `K42_S05` | `değişimlerin, soğanın` | `değişimlerin soğanın` | Fazla ',' -> non (p=1.000) |

---

## 3. Araç 2: `hunspell-tr` (`spylls`)

### 3.1. Ölçüt Tablosu — (a) Yanlış Alarm Süzgeci ve (b) Bulucu

- **Sözlük yükleme süresi:** 3,98 sn; **60 sayfa tarama süresi:** **35,84 sn** (sayfa başına **0,597 sn**, 300 sayfa için **~3,0 dk**).

| Kullanım | Küme | Ölçüt | Gerçekleşen | Karar |
|---|---|---|---|---|
| **(a) Yanlış alarm süzgeci** | Hakemli gösterilen B `morfoloji` (79 tespit: 13 `HATA`, 66 `DEGIL`) | `HATA` kaybı $\le 1$ **ve** `DEGIL` inen $\ge \%30$ | `HATA` kaybı: **1/13** (`sorumluklar`), `DEGIL` inen: **11/66 (\%16,7)** | **Kapatıldı** ✗ |
| **(a) Yanlış alarm süzgeci** | Birleşik B `morfoloji` (144 tespit: 18 `HATA`, 124 `DEGIL`, 2 `BELIRSIZ`) | `HATA` kaybı $\le 1$ **ve** `DEGIL` inen $\ge \%30$ | `HATA` kaybı: **1/18** (`sorumluklar`), `DEGIL` inen: **15/124 (\%12,1)** | **Kapatıldı** ✗ |
| **(b) Bulucu** | 60 A sayfası (ürün süzgeçleri sonrası) | `kelime` sınıfı $\ge 3/9$ **ve** eşleşmeyen $< 1,0$/sayfa | `kelime` sınıfı: **1/9** (`K45_A29` `işaretleyiz`), eşleşmeyen: **22 (0,37/sayfa)** | **Kapatıldı** ✗ |
| **(b) Bulucu (Ham)** | 60 A sayfası (terim/alıntı süzgeci öncesi) | `kelime` sınıfı $\ge 3/9$ **ve** eşleşmeyen $< 1,0$/sayfa | `kelime` sınıfı: **1/9** (`K45_A29` `işaretleyiz`), eşleşmeyen: **99 (1,65/sayfa)** | **Kapatıldı** ✗ |

### 3.2. (a) Süzgeç Ayrıntıları

- **Kaybedilen gerçek hata (1 adet):** `K42_B30` (`biyoloji11` s. 139) `sorumluklar` — `hunspell-tr` sözlüğünde `sorumluk` kökü tanımlı olduğu için bu gerçek yazım hatasını geçerli saydı.
- **Düşürülen yanlış alarmlar (Hakemli B'de 11/66):** `seçik` (`K42_B02`), `püskü` (`K42_B08`), `üzre` (`K42_B10`), `nefs` (`K42_B12`), `duymayagöreyim` (`K42_B31`), `şehid` (`K45_B110`), `bloka` (`K45_B120`), `arşa` (`K45_B124`), `çiftli` (`K45_B17`), `bloka` (`K45_B23`), `cevab` (`K45_B54`)
- Yanlış alarmların geri kalan %83,3'ü (`transkripsiyonu`, `ökaryot`, `kemoototrof`, `meristem`, `siyanobakteriler`, `allosterik` vb. biyoloji terimleri ve eski Türkçe kelimeler) `hunspell-tr` sözlüğünde de yer almadığı için süzülemedi.

### 3.3. (b) Bulucu: Bulunan ve Kaçırılan `kelime` Sınıfı Hatalar

- **Bulunan (1/9):** `K45_A29` (`K45_S14`, `biyoloji12` s. 186): `işaretleyiz` $\rightarrow$ `işaretleyiniz` (Starlang ve Zemberek `işaretle-y-iz` olarak çözümlediği hâlde `hunspell-tr` reddetti; mevcut sistem bunu bulamıyordu).
- **Kaçırılan `kelime` sınıfı hatalar (8/9):**
  - `K42_A04` (`K42_S02`): `Commasie` $\rightarrow$ `Coomassie`
  - `K42_A07` (`K42_S06`): `coğrafik` $\rightarrow$ `coğrafi`
  - `K42_A11` (`K42_S08`): `Canidea` $\rightarrow$ `Canidae`
  - `K42_A23` (`K42_S21`): `gr` $\rightarrow$ `g`
  - `K42_A36` (`K42_S25`): `’abesdir` $\rightarrow$ `abestir`
  - `K45_A58` (`K45_S25`): `kollektifleştirme` $\rightarrow$ `kolektifleştirme`
  - `K45_A64` (`K45_S29`): `COVİD-19` $\rightarrow$ `COVID-19`
  - `K45_A66` (`K45_S30`): `Yarımada’yı` $\rightarrow$ `yarımadayı`
  *(Not: `coğrafik` ve `kollektifleştirme` zaten Starlang/Zemberek tarafından da reddedildiği için 'Starlang+Zemberek geçerli' kümesinde değildir; `Commasie`, `Canidea`, `COVİD-19`, `Yarımada’yı` büyük harf/özel ad/kesme kurallarıyla atlanır; `gr` 2 harfli kısaltma olduğu için atlanır ve ayrıca `hunspell-tr` `gr`'yi geçerli saymaktadır; `’abesdir` ise alıntı dizesindedir ve Starlang/Zemberek tarafından da reddedilmektedir.)*

### 3.4. (b) Bulucu: 10 Rastgele Eşleşmeyen İşaret Örneği (Tohum `20261117`)

| # | Sayfa | Kitaptaki Kelime | Gerekçe |
|---|---|---|---|
| 1 | `K45_S16` | `ünvanlara` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 2 | `K42_S21` | `nâzırı` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 3 | `K42_S11` | `hâle` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 4 | `K42_S05` | `difüzyona` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 5 | `K45_S20` | `hâle` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 6 | `K42_S29` | `mübârek` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 7 | `K42_S25` | `tuyuğu` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 8 | `K42_S29` | `âteşlerini` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 9 | `K42_S04` | `âlemlerde` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |
| 10 | `K45_S20` | `hükümetine` | Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı |

### 3.5. (c) Bilgi İçin: `hunspell-tr` Öneri Kalitesi (`kelime` Sınıfındaki 9 Gerçek Hata)

`kelime` sınıfındaki 9 gerçek hatanın **4'ünde (%44,4)** doğru yazım `hunspell.suggest()` ilk 3 önerisi içinde yer aldı:

| ID | Kitaptaki | Doğrusu | Hunspell Geçerli mi? | İlk 3 Öneri | İlk 3'te Doğru Var mı? |
|---|---|---|---|---|---|
| `K42_A04` | `Commasie` | `Coomassie` | Hayır | `Sinemasko` | ✗ Hayır |
| `K42_A07` | `coğrafik` | `coğrafi` | Hayır | `coğrafi`, `coğrafin`, `coğraf ik` | ✓ Evet |
| `K42_A11` | `Canidea` | `Canidae` | Hayır | `Canide`, `Caniden`, `Can idea` | ✗ Hayır |
| `K42_A23` | `gr` | `g` | Evet | `rg`, `fr`, `ge` | ✗ Hayır |
| `K42_A36` | `’abesdir` | `abestir` | Hayır | `abestir`, `abes dir`, `abes-dir` | ✓ Evet |
| `K45_A29` | `işaretleyiz` | `işaretleyiniz` | Hayır | `işaretleyi`, `işaretliyiz`, `işaretleyiş` | ✗ Hayır |
| `K45_A58` | `kollektifleştirme` | `kolektifleştirme` | Hayır | `kolektifleştirme`, `kolektifleştir`, `kolektifleşti` | ✓ Evet |
| `K45_A64` | `COVİD-19` | `COVID-19` | Hayır | *(öneri yok)* | ✗ Hayır |
| `K45_A66` | `Yarımada’yı` | `yarımadayı` | Hayır | `Yarımadayı`, `Yarımadası`, `Yarımada` | ✓ Evet |

---

## 4. Araç 3: Yerel Modelle Sayfa Okuma (Temiz Blok Metniyle)

K43'teki deneyde ham `A_30_sayfa_metin.txt` içindeki yumuşak tireler (`U+00AD`) 67 adayın 50'sini sahte tire hatasına dönüştürmüştü. Bu taramada modellere doğrudan ürünün temizlenmiş blok metinleri (`veri/<kitap>_bloklar.json`) K43 ile birebir aynı sistem istemi, soru şablonu ve JSON şemasıyla (`temperature=0`, `num_ctx=4096`, `num_predict=1024`) verildi.

### 4.1. Model Karşılaştırma ve Ölçüt Tablosu

| Ölçüt / Gösterge | Geçme Eşiği | `qwen3.5:9b` | `gemma4:12b-it-qat` |
|---|---|---|---|
| **Bulunan gerçek hata (/44)** | $\ge 15 / 44$ | **12 / 44** (%27,3) ✗ | **19 / 44** (%43,2; sıkı: **18 / 44**, %40,9) ✓ |
| **Mevcut sistemin bulmadığı (ek hata)** | $\ge 8$ | **6** ✗ | **12** (sıkı: **11**) ✓ |
| **Toplam aday / sayfa başı aday** | $< 3,0$ / sayfa ($< 180$) | 176 (**2,93 / sayfa**) ✓ | 135 (**2,25 / sayfa**) ✓ |
| `noktalama` sınıfı bulunan (/13) | *(Bilgi)* | 3 / 13 | 6 / 13 |
| `kelime` sınıfı bulunan (/9) | *(Bilgi)* | 2 / 9 | 5 / 9 (sıkı: 4 / 9) |
| `diger` sınıfı bulunan (/22) | *(Bilgi)* | 7 / 22 | 8 / 22 |
| Eşleşmeyen aday sayısı | *(Bilgi)* | 162 (2,70 / sayfa) | 115 (1,92 / sayfa) |
| Kurulun `DEGIL` dediğiyle eşleşen aday | *(Bilgi)* | 11 | 8 |
| JSON şema / kesilme hatası olan sayfa | *(Bilgi)* | **23 / 60 sayfa** | **1 / 60 sayfa** (`K45_S11`) |
| Toplam süre (60 sayfa) | *(Bilgi)* | 1078,5 sn (~18,0 dk) | 912,3 sn (~15,2 dk) |
| Sayfa başına ortalama süre | *(Bilgi)* | **17,98 sn / sayfa** | **15,21 sn / sayfa** |
| **300 sayfalık kitap tahmini süre** | *(Bilgi)* | **~89,9 dk (~1,5 saat)** | **~76,0 dk (~1,27 saat)** |
| **Karar** | Tüm ölçütler ✓ | **Kapatıldı** ✗ | **Geçti** ✓ |

### 4.2. `qwen3.5:9b` Ayrıntıları (Kapatıldı)

**Bulunan gerçek hatalar (12/44; mevcut sistemin bulmadığı 6 hata `(+)` ile işaretli):**
- `K42_A05` (`K42_S03`, `noktalama`): `yazınız..` $\rightarrow$ `yazınız.` | Model: `Sazancıkların bulunduğu havuza nakledilmiş olan lepistesler, 22 ay sonra yeniden lepistes kaynak havuzuna döndürülürse ne olacağına dönük tahmininizi yazınız..` $\rightarrow$ `Sazancıkların bulunduğu havuza nakledilmiş olan lepistesler, 22 ay sonra yeniden lepistes kaynak havuzuna döndürülürse ne olacağına dair tahmininizi yazınız.`
- `K42_A09` (`K42_S08`, `noktalama`): `11,12, 13` $\rightarrow$ `11, 12, 13` | Model: `11,12, 13 ve 14.` $\rightarrow$ `11., 12., 13. ve 14.`
- `K42_A10` `(+)` (`K42_S08`, `diger`): `Canis familaris` $\rightarrow$ `Canis familiaris` | Model: `Canis familaris` $\rightarrow$ `Canis familiaris`
- `K42_A11` `(+)` (`K42_S08`, `kelime`): `Canidea` $\rightarrow$ `Canidae` | Model: `Canidea` $\rightarrow$ `Canidae`
- `K45_A01` (`K45_S01`, `diger`): `1953’ te` $\rightarrow$ `1953’te` | Model: `25 Nisan 1953’ te` $\rightarrow$ `25 Nisan 1953'te`
- `K45_A05` (`K45_S03`, `diger`): `Görsel 2.2 ‘de` $\rightarrow$ `Görsel 2.2’de` | Model: `Görsel 2.2 ‘de` $\rightarrow$ `Görsel 2.2'de`
- `K45_A13` `(+)` (`K45_S07`, `noktalama`): `gece gündüz fotosentezi` $\rightarrow$ `gece gündüz, fotosentezi` | Model: `Bitkiler solunumu gece gündüz fotosentezi sadece ışık varlığında yapar.` $\rightarrow$ `Bitkiler **hem** solunumunu **gece ve gündüz** **yapar**, hem de fotosentezi sadece ışık varlığında gerçekleştirir.`
- `K45_A14` (`K45_S07`, `diger`): `H2S’ dir` $\rightarrow$ `H2S’dir` | Model: `Reaksiyona giren maddeler CO2 ve H2O veya H2S' dir.` $\rightarrow$ `Reaksiyona giren maddeler CO₂ ve H₂O veya H₂S'dir.`
- `K45_A17` `(+)` (`K45_S07`, `diger`): `Farklı yönleri` $\rightarrow$ `Farklı Yönleri` | Model: `Fotosentez ve oksijenli solunumun farklı yönleri Tablo 2.6' da gösterilmiştir.` $\rightarrow$ `Fotosentez ve oksijenli solunumun farklı yönleri Tablo 2.6'da gösterilmiştir.` *(Not: model tablo başlığını değil, paragraftaki `'...farklı yönleri Tablo 2.6’ da...'` cümlesini kesme boşluğu için alıntıladığından `Farklı yönleri` ile mekanik eşleşti)*
- `K45_A22` (`K45_S11`, `diger`): `%78’ i` $\rightarrow$ `%78’i` | Model: `Atmosferin %78’ i azot olsa da bitkiler bu serbest azotu kullanamaz, azotu topraktaki amonyum ve nitrat bileşiklerinden karşılar.` $\rightarrow$ `Atmosferin %78'i azottur; ancak bitkiler bu serbest azotu doğrudan kullanamaz, bunun yerine topraktaki amonyum ve nitrat bileşiklerinden azot alırlar.`
- `K45_A63` `(+)` (`K45_S29`, `diger`): `suv modeli` $\rightarrow$ `SUV modeli` | Model: `Görsel 8.8: Yerli otomobilin suv modeli` $\rightarrow$ `Görsel 8.8: Yerli otomobilin SUV modeli`
- `K45_A66` `(+)` (`K45_S30`, `kelime`): `Yarımada’yı` $\rightarrow$ `yarımadayı` | Model: `Yarımada'yı kana bulamışlardır.` $\rightarrow$ `Yarımadayı kana bulamışlardır.`

**Kaçırılan gerçek hatalar (32/44):** `K42_A02`, `K42_A04`, `K42_A07`, `K42_A08`, `K42_A14`, `K42_A15`, `K42_A17`, `K42_A18`, `K42_A23`, `K42_A29`, `K42_A36`, `K42_A50`, `K42_A79`, `K45_A02`, `K45_A04`, `K45_A06`, `K45_A08`, `K45_A15`, `K45_A19`, `K45_A20`, `K45_A23`, `K45_A24`, `K45_A28`, `K45_A29`, `K45_A39`, `K45_A46`, `K45_A51`, `K45_A52`, `K45_A53`, `K45_A58`, `K45_A60`, `K45_A64`

**`qwen3.5:9b` — 10 Rastgele Eşleşmeyen İşaret Örneği (Tohum `20261117`):**

| # | Sayfa | Kitaptaki Parça | Model Önerisi | Gerekçe |
|---|---|---|---|---|
| 1 | `K42_S21` | `Şemun suyunu hepsinden hafif ve mutedil hazmı kolay bir hayat suyu buldular.` | `Şemun suyunu, hepsinden hafif ve mutedil, hazımı kolay bir hayat suyu buldular.` | Cümle yapısı bozuk; 'hazmı' kelimesi yanlış kullanılmış. |
| 2 | `K45_S13` | `Deneyin Tasarlanması: 20 dakika, Tasarının sunumu: 20 dakika` | `Deneyin tasarlanması: 20 dakika, Tasarının sunulması: 20 dakika` | 'Tasarının' kelimesi yanlış yazılmıştır. Doğru kullanım: 'Tasarının' yerine 'sunulması' olmalıdır. |
| 3 | `K42_S28` | `Batı'dan alınan yeni nazım biçimleri kullanılmıştır.` | `Batı'dan alınan yeni nazım biçimleri kullanılmıştır.` | Bu cümlede hata bulunmamaktadır. |
| 4 | `K42_S25` | `Nazım Şekilleri ve Aruz)` | `Nazım Şekilleri ve Arûz)` | 'Aruz' kelimesi 'Arûz' olarak yazılmalıdır. |
| 5 | `K42_S27` | `lahza eksik olmuyordu` | `lahza eksik olmuyordu` | Yanlış: 'lahza' kelimesi zaman birimi olarak kullanılırken, cümledeki anlam bağlamı gereği 'bir lahza bile eksik olmuyordu' şeklinde tamamlanmalıdır. Ancak asıl hata: 'tedirginliğe' kelimesinin yazımı doğrudur ancak cümlenin akışı bozucu bir noktalama hatası vardır. |
| 6 | `K45_S07` | `Fotosentez ve oksijenli solunumun ortak yönleri ise enzim kullanılması, ATP üretimi ve tüketimi, ETS elemanlarının görev alması ve enerji dönüşümleridir.` | `Fotosentez ve oksijenli solunumun ortak yönleri ise enzim kullanılması, ATP üretimi ve tüketimi, ETS elemanlarının görev alması ve enerji dönüşümleridir.` | "ETS" kelimesinin baş harfi büyük olmalıdır. |
| 7 | `K45_S04` | `Nikola Tüudör Dö Suçyu` | `Nicolas Theodore De Saussure` | Yabancı isimlerin yazımı hatalıdır. Doğrusu 'Nicolas Theodore De Saussure' olmalıdır. |
| 8 | `K45_S11` | `Mikoriza, bazı bitkilerin kökleri ile topraktaki özel mantarların oluşturduğu simbiyotik birliktir (Görsel 3.74).` | `Mikoriza, bazı bitkilerin kökleri ile topraktaki özel mantarların oluşturduğu simbiyotik birlikteliştir (Görsel 3.74).` | Cümlenin sonu nokta ile bittiği için 'birliktir' kelimesinden sonra eksik bir isim çekimi veya bağlaç bulunmamaktadır; cümle yapısal olarak tamamlanmamıştır ('birliktir' yerine 'birlikteliştir' kullanılmalı). |
| 9 | `K45_S23` | `yaldızlı dağlar petrolle sulanıyordu.` | `yaldızlı dağlar petrolle sulanıyordu.` | Metin, alıntı olduğu için (Georges Langlois) ağız özellikleri veya eski kullanım hata sayılmaz. |
| 10 | `K42_S03` | `Nakledilen lepistes popülasyonundaki erkeklerin benek sayısında azalma fakat beneklerin kapladığı toplam alanda bir artış gözlemlenmiştir.` | `Nakledilen lepistes popülasyonundaki erkeklerin benek sayısında azalma, fakat beneklerin kapladığı toplam alanda bir artış gözlemlenmiştir.` | Cümle içindeki 'azalma fakat' ifadesi yerine 'azalma, fakat' şeklinde virgül kullanımı cümlenin okunabilirliğini artırır. |

### 4.3. `gemma4:12b-it-qat` Ayrıntıları (Geçti)

Temiz blok metni verildiğinde `gemma4:12b-it-qat`'ın K43'teki sahte tire sorunu tamamen ortadan kalktı (K43'te 30 sayfada 67 adayın 50'si sahte tire iken, K47'de 60 sayfada 135 adayın yalnızca 1 tanesinde satır sonu tire birleşimi geçti). Model 44 gerçek hatanın **19'unu** (mekanik; `K42_A36` alıntı açıklaması çıkarıldığında **18'ini**) yakaladı ve mevcut sistemin (`HEAD`) kaçırdığı **12 gerçek hatayı** (sıkı: **11**) buldu.

**Bulunan gerçek hatalar (19/44; mevcut sistemin bulmadığı 12 hata `(+)` ile işaretli):**
- `K42_A04` `(+)` (`K42_S02`, `kelime`): `Commasie` $\rightarrow$ `Coomassie` | Model: `Commasie (Komasi)` $\rightarrow$ `Coomassie (Komasi)` (Laboratuvar ortamında kullanılan boyanın adı 'Coomassie'dir. 'Commasie' yazımı bir yazım hatasıdır.)
- `K42_A05` (`K42_S03`, `noktalama`): `yazınız..` $\rightarrow$ `yazınız.` | Model: `yazınız..` $\rightarrow$ `yazınız.` (Cümlenin sonunda gereksiz yere çift nokta kullanılmıştır.)
- `K42_A08` (`K42_S07`, `noktalama`): `Yönerge :` $\rightarrow$ `Yönerge:` | Model: `Yönerge :` $\rightarrow$ `Yönerge:` (İki noktadan önce boşluk bırakılmaz.)
- `K42_A09` (`K42_S08`, `noktalama`): `11,12, 13` $\rightarrow$ `11, 12, 13` | Model: `11,12, 13 ve 14. soruları` $\rightarrow$ `11, 12, 13 ve 14. soruları` (Sayılar arasında virgül kullanımından sonra boşluk bırakılmalıdır.)
- `K42_A11` `(+)` (`K42_S08`, `kelime`): `Canidea` $\rightarrow$ `Canidae` | Model: `Canidea` $\rightarrow$ `Canidae` (Taksonomide 'Canidea' diye bir aile ismi yoktur, doğru yazımı 'Canidae' şeklindedir.)
- `K42_A17` `(+)` (`K42_S19`, `diger`): `Kap atışı` $\rightarrow$ `Kalp atışı` | Model: `Kap atışı` $\rightarrow$ `Kalp atışı` (Bağlam gereği (stres ve korku durumunda artan fizyolojik tepki), 'Kap atışı' ifadesi 'Kalp atışı' ifadesinin yanlış yazımıdır.)
- `K42_A36` `(+)` (`K42_S25`, `kelime`): `’abesdir` $\rightarrow$ `abestir` | Model: `Etsem de ‘abesdir sitem-i hâra tahammül` $\rightarrow$ `Etsem de ‘abesdir sitem-i hâra tahammül` (Metin içerisinde yer alan bu dize bir şiir/eski metin alıntısı olduğu için kural gereği hata olarak sayılmamıştır.) *(Mekanik eşleşme notu: model bu dizeyi `'şiir/eski metin alıntısı olduğu için hata olarak sayılmamıştır'` gerekçesiyle `kitaptaki == onerilen` olarak döndürdü; bu satır elendiğinde dahi 18/44 bulunan ve 11 ek hata ile tüm ölçütler sağlanmaktadır.)*
- `K42_A79` (`K42_S30`, `noktalama`): `1947,1962` $\rightarrow$ `1947, 1962` | Model: `1947,1962` $\rightarrow$ `1947, 1962` (Sayıların arasına konulan virgülün ardından bir boşluk bırakılmalıdır.)
- `K45_A01` (`K45_S01`, `diger`): `1953’ te` $\rightarrow$ `1953’te` | Model: `1953’ te` $\rightarrow$ `1953'te` (Kesme işaretinden sonra boşluk bırakılmaz.)
- `K45_A04` (`K45_S02`, `diger`): `Görsel 1.8’ de` $\rightarrow$ `Görsel 1.8’de` | Model: `Görsel 1.8’ de` $\rightarrow$ `Görsel 1.8’de` (Kesme işaretinden sonra gelen ek (de/da) bitişik yazılmalıdır.)
- `K45_A05` (`K45_S03`, `diger`): `Görsel 2.2 ‘de` $\rightarrow$ `Görsel 2.2’de` | Model: `Görsel 2.2 ‘de` $\rightarrow$ `Görsel 2.2’de` (Kesme işareti, kelimenin son harfine bitişik yazılmalıdır.)
- `K45_A13` `(+)` (`K45_S07`, `noktalama`): `gece gündüz fotosentezi` $\rightarrow$ `gece gündüz, fotosentezi` | Model: `Bitkiler solunumu gece gündüz fotosentezi sadece ışık varlığında yapar.` $\rightarrow$ `Bitkiler solunumu gece gündüz, fotosentezi sadece ışık varlığında yapar.` (Cümledeki özne ve yüklem uyumunu sağlamak, anlam karışıklığını önlemek ve okumayı kolaylaştırmak için 'gece gündüz' ifadesinden sonra virgül kullanılmalıdır.)
- `K45_A17` `(+)` (`K45_S07`, `diger`): `Farklı yönleri` $\rightarrow$ `Farklı Yönleri` | Model: `Tablo 2.6: Fotosentez ile Oksijenli Solunumun Farklı yönleri` $\rightarrow$ `Tablo 2.6: Fotosentez ile Oksijenli Solunumun Farklı Yönleri` (Başlıklarda özel isim niteliği taşıyan veya vurgulanan kelimelerin ilk harfleri büyük yazılmalıdır; 'Yönleri' kelimesinin baş harfi büyük olmalıdır.)
- `K45_A20` `(+)` (`K45_S10`, `diger`): `Yaprağının enine kesitinde` $\rightarrow$ `Yaprağın enine kesitinde` | Model: `Görsel 3.22: Yaprağının enine kesitinde alt ve üst epidermis tabakası` $\rightarrow$ `Görsel 3.22: Yaprağın enine kesitinde alt ve üst epidermis tabakası` (Tamlama hatası mevcuttur. 'Yaprağının' (onun yaprağı) yerine 'Yaprağın' (yaprak nesnesinin) kullanılmalıdır.)
- `K45_A23` `(+)` (`K45_S12`, `noktalama`): `Ksilemdeki su ,` $\rightarrow$ `Ksilemdeki su,` | Model: `Ksilemdeki su ,` $\rightarrow$ `Ksilemdeki su,` (Virgül işaretinden önce boşluk bırakılmamalıdır.)
- `K45_A24` `(+)` (`K45_S12`, `diger`): `Ksilem de` $\rightarrow$ `Ksilemde` | Model: `Ksilem de` $\rightarrow$ `Ksilemde` (Bulunma durumu eki olan '-de' bitişik yazılmalıdır.)
- `K45_A29` `(+)` (`K45_S15`, `kelime`): `işaretleyiz` $\rightarrow$ `işaretleyiniz` | Model: `seçeneği işaretleyiz.` $\rightarrow$ `seçeneği işaretleyiniz.` (Soru kökünde öğrenciye hitap edildiği için emir kipi (işaretleyiniz) kullanılmalıdır. 'İşaretleyiz' ifadesi birinci çoğul şahıs geniş zamanıdır ve soru formatına uygun değildir.)
- `K45_A63` `(+)` (`K45_S29`, `diger`): `suv modeli` $\rightarrow$ `SUV modeli` | Model: `suv modeli` $\rightarrow$ `SUV modeli` (Kısaltmalar büyük harfle yazılır.)
- `K45_A64` `(+)` (`K45_S29`, `kelime`): `COVİD-19` $\rightarrow$ `COVID-19` | Model: `COVİD-19` $\rightarrow$ `COVID-19` (Uluslararası literatürde ve genel kullanımda 'I' harfi yerine 'I' (İngilizce karakteri) kullanılır; ancak Türkçe metinlerde bazen yerelleştirme yapılsa da standart yazım COVID-19 şeklindedir.)

**Kaçırılan gerçek hatalar (25/44):**
- `K42_A02` (`K42_S02`, `diger`): `Form11` $\rightarrow$ `Form 11`
- `K42_A07` (`K42_S06`, `kelime`): `coğrafik` $\rightarrow$ `coğrafi`
- `K42_A10` (`K42_S08`, `diger`): `Canis familaris` $\rightarrow$ `Canis familiaris`
- `K42_A14` (`K42_S18`, `noktalama`): `akıllı termostatlar;` $\rightarrow$ `akıllı termostatlar`
- `K42_A15` (`K42_S18`, `noktalama`): `örnek veriniz?` $\rightarrow$ `örnek veriniz.`
- `K42_A18` (`K42_S20`, `noktalama`): `solunum hızı;` $\rightarrow$ `solunum hızı,`
- `K42_A23` (`K42_S21`, `kelime`): `gr` $\rightarrow$ `g`
- `K42_A29` (`K42_S24`, `diger`): `bir takım vasıflar` $\rightarrow$ `birtakım vasıflar`
- `K42_A50` (`K42_S27`, `diger`): `Sözlü alarak ifade ediniz.` $\rightarrow$ `Sözlü olarak ifade ediniz.`
- `K45_A02` (`K45_S01`, `noktalama`): `(Görsel 1.2)],1869` $\rightarrow$ `(Görsel 1.2)], 1869`
- `K45_A06` (`K45_S03`, `diger`): `tepkimelerine endergonik tepkimeler, enerji açığa çıkaran tepkimelerine ise` $\rightarrow$ `tepkimelere endergonik tepkimeler, enerji açığa çıkaran tepkimelere ise`
- `K45_A08` (`K45_S04`, `diger`): `Engelman deneyi` $\rightarrow$ `Engelmann deneyi`
- `K45_A14` (`K45_S07`, `diger`): `H2S’ dir` $\rightarrow$ `H2S’dir`
- `K45_A15` (`K45_S07`, `diger`): `O2 dir` $\rightarrow$ `O2’dir`
- `K45_A19` (`K45_S10`, `noktalama`): `Kloroplast içermez bu yüzden` $\rightarrow$ `Kloroplast içermez, bu yüzden`
- `K45_A22` (`K45_S11`, `diger`): `%78’ i` $\rightarrow$ `%78’i`
- `K45_A28` (`K45_S14`, `diger`): `Oksin hormonun` $\rightarrow$ `Oksin hormonunun`
- `K45_A39` (`K45_S20`, `noktalama`): `Kazım Karabekir;` $\rightarrow$ `Kazım Karabekir`
- `K45_A46` (`K45_S20`, `noktalama`): `riya tembellik` $\rightarrow$ `riya, tembellik`
- `K45_A51` (`K45_S21`, `diger`): `Türkiye Cumhuriyetine` $\rightarrow$ `Türkiye Cumhuriyeti’ne`
- `K45_A52` (`K45_S22`, `diger`): `ve tabi bu arada` $\rightarrow$ `ve tabii bu arada`
- `K45_A53` (`K45_S22`, `diger`): `Büyük Millet Meclis` $\rightarrow$ `Büyük Millet Meclisi`
- `K45_A58` (`K45_S25`, `kelime`): `kollektifleştirme` $\rightarrow$ `kolektifleştirme`
- `K45_A60` (`K45_S27`, `diger`): `Demokrat Parti (DP)’nin` $\rightarrow$ `Demokrat Partinin (DP)`
- `K45_A66` (`K45_S30`, `kelime`): `Yarımada’yı` $\rightarrow$ `yarımadayı`

**`gemma4:12b-it-qat` — 10 Rastgele Eşleşmeyen İşaret Örneği (Tohum `20261117`):**

| # | Sayfa | Kitaptaki Parça | Model Önerisi | Gerekçe |
|---|---|---|---|---|
| 1 | `K45_S27` | `Demokratik bir seçim kanununun` | `Demokratik bir seçim kanununun` | Metinde 'kanununun' şeklinde bir kullanım görünmüyor ancak 'kanununun' ifadesi dil bilgisi açısından hatalıdır. Eğer metinde 'kanununun' şeklinde bir yazım varsa 'kanunun' şeklinde düzeltilmelidir. Mevcut metinde 'kanununun' yazmıyor, 'kanununun' ifadesi yerine 'kanunun' kullanılmalıdır. Ancak metinde 'kanununun' geçmediği için bu maddeyi kontrol ediniz. |
| 2 | `K42_S04` | `beklenmektedir. beklenmektedir.` | `beklenmektedir.` | Cümle sonu ifadesi tekrarlanmış (dizgi hatası). |
| 3 | `K42_S26` | `Gel, al şunu da, Bir mısır tanesi ver bana.` | `Gel, al şunu da, Bir mısır tanesi ver bana.` | Şiir/masal alıntısı olduğu için mısra başı büyük harf kullanımı korunmuştur. |
| 4 | `K42_S11` | `elektriksel, göçmen kuşlar ve bazı balıklardaki manyetoreseptörler` | `elektriksel uyaranları; göçmen kuşlar ve bazı balıklardaki manyetoreseptörler` | Bilgi kutusu metni parçalanmış ve kelimeler birbirine karışmış görünüyor. 'Elektriksel' kelimesi muhtemelen 'elektriksel uyaranları' ifadesinin parçasıdır. Cümle yapısı bozulduğu için noktalama ve kelime düzenlemesi gerekmektedir. |
| 5 | `K42_S07` | `biyoçeşitliliği` | `biyoçeşitliliği` | Metin içerisinde 'biyolojik çeşitlilik' ve 'biyoçeşitlilik' kavramları birbirinin yerine kullanılmıştır. Ders kitabı standartları gereği kavram birliği sağlanmalıdır. |
| 6 | `K42_S08` | `diğer ifadeyle tür, temel sınıflandırma birimidir.` | `diğer ifadeyle tür, temel sınıflandırma birimidir.` | Cümle çok uzun ve karmaşık. '...canlı grubu; diğer ifadeyle tür, temel sınıflandırma birimidir.' şeklinde noktalı virgül kullanımı anlamı güçlendirebilir. |
| 7 | `K42_S30` | `coşa taşa` | `coşa taşa` | Metin içerisinde 'coşa taşa' ifadesi yer almaktadır. Bu ifade bir deyim veya özel bir kullanım değilse, 'coşa taşa' şeklinde yazılması doğrudur ancak bağlamda 'coşa taşa' yerine 'coşa taşa' (veya 'coşa taşa' gibi bir yazım hatası olup olmadığı) kontrol edilmelidir. Ancak mevcut haliyle 'coşa taşa' ifadesi bir yazım hatası gibi durmamaktadır, sadece kelime seçimi alışılmadık olabilir. Eğer 'coşa taşa' yerine 'coşa taşa' kastediliyorsa düzeltilmelidir. Ancak metin akışında bir hata görülmemektedir. |
| 8 | `K42_S25` | `Pây-mâl eyledi bu zülf-i semen-sâ nidelim` | `Pây-mâl eyledi bu zülf-i semen-sâ nidelim` | Metin içerisinde yer alan bu dize bir şiir/eski metin alıntısı olduğu için kural gereği hata olarak sayılmamıştır. |
| 9 | `K45_S01` | `mitokondri, kloroplast ve ribozomlarında;` | `mitokondri, kloroplast ve ribozomlarında` | Cümle içinde, sıralı öğelerden sonra noktalı virgül kullanımı bu bağlamda gereksizdir; virgül yeterlidir veya hiçbir işaret konulmadan devam edilebilir. |
| 10 | `K45_S05` | `C6 H12O6` | `C6H12O6` | Dizgi hatası. Kimyasal formüllerde atom sembolleri ve alt indisler arasında boşluk bırakılmaz. |

---

## 5. Birleşik Tablo: Mevcut Sistem ve Mevcut Sistem + Geçen Araç (`gemma4:12b-it-qat`)

Ön kayıt ölçütlerini yalnız **Araç 3 (`gemma4:12b-it-qat` ile temiz blok metni üzerinden sayfa okuma)** geçti.

| Sistem Bileşimi | `noktalama` (/13) | `kelime` (/9) | `diger` (/22) | Toplam Bulunan (/44) | Bulma Oranı |
|---|---|---|---|---|---|
| **Mevcut sistem (`HEAD`, `ce96bf8`) tek başına** | 5/13 | 3/9 | 7/22 | **15 / 44** | **%34,1** |
| **`gemma4:12b-it-qat` tek başına (mekanik)** | 6/13 | 5/9 | 8/22 | **19 / 44** | **%43,2** |
| **`gemma4:12b-it-qat` tek başına (`kitaptaki != onerilen` süzgeçli)** | 6/13 | 4/9 | 8/22 | **18 / 44** | **%40,9** |
| **Mevcut sistem + `gemma4:12b-it-qat` (mekanik birleşim)** | 7/13 | 8/9 | 12/22 | **27 / 44** | **%61.4** |
| **Mevcut sistem + `gemma4:12b-it-qat` (`kitaptaki != onerilen` süzgeçli)** | 7/13 | 7/9 | 12/22 | **26 / 44** | **%59.1** |

### 5.1. Kümelerin Kesişimi ve Tamamlayıcılığı

- **Her ikisinin de yakaladığı (7 hata):** `K42_A05`, `K42_A08`, `K42_A09`, `K42_A79`, `K45_A01`, `K45_A04`, `K45_A05`
- **Yalnız mevcut sistemin (`HEAD`) yakaladığı (8 hata):** `K42_A02` (`Form11`), `K42_A07` (`coğrafik`), `K42_A15` (`örnek veriniz?`), `K42_A23` (`gr`), `K42_A29` (`bir takım vasıflar`), `K45_A14` (`H2S’ dir`), `K45_A22` (`%78’ i`), `K45_A58` (`kollektifleştirme`)
- **Yalnız `gemma4:12b-it-qat`'ın yakaladığı (11 gerçek hata + 1 mekanik `K42_A36`):** `K42_A04` (`Commasie` $\rightarrow$ `Coomassie`), `K42_A11` (`Canidea` $\rightarrow$ `Canidae`), `K42_A17` (`Kap atışı` $\rightarrow$ `Kalp atışı`), `K45_A13` (`gece gündüz fotosentezi` $\rightarrow$ `gece gündüz, fotosentezi`), `K45_A17` (`Farklı yönleri` $\rightarrow$ `Farklı Yönleri`), `K45_A20` (`Yaprağının enine kesitinde` $\rightarrow$ `Yaprağın enine kesitinde`), `K45_A23` (`Ksilemdeki su ,` $\rightarrow$ `Ksilemdeki su,`), `K45_A24` (`Ksilem de` $\rightarrow$ `Ksilemde`), `K45_A29` (`işaretleyiz` $\rightarrow$ `işaretleyiniz`), `K45_A63` (`suv modeli` $\rightarrow$ `SUV modeli`), `K45_A64` (`COVİD-19` $\rightarrow$ `COVID-19`)
- **İkisinin de kaçırdığı (18 hata):** `K42_A10`, `K42_A14`, `K42_A18`, `K42_A36`, `K42_A50`, `K45_A02`, `K45_A06`, `K45_A08`, `K45_A15`, `K45_A19`, `K45_A28`, `K45_A39`, `K45_A46`, `K45_A51`, `K45_A52`, `K45_A53`, `K45_A60`, `K45_A66`

---

## 6. Ön Kayıttan Sapma ve Teknik Gözlemler

1. **Ön kayıttan sapma yoktur:** `testseti/k47_on_kayit.md` içinde kilitlenen hata sınıfları, eşleşme kuralı, eşikler (`0,95`, `%30`, `15/44`, `8 ek hata`, `< 3,0 aday/sayfa`), sistem istemi ve JSON şeması hiçbir araçta değiştirilmemiştir.
2. **`qwen3.5:9b` JSON kesilme sorunu:** `qwen3.5:9b`, `num_predict=1024` sınırında 60 sayfanın 23'ünde çok sayıda sahte/uzun açıklama üretmeye çalışırken JSON çıktısını tamamlayamadı (`yerel_model.sohbet` `None` döndü). K43'te de aynı model 30 sayfanın 9'unda aynı sebeple boş dönmüştü.
3. **`gemma4:12b-it-qat` JSON kararlılığı ve `kitaptaki == onerilen` gözlemi:** `gemma4:12b-it-qat` 60 sayfanın 59'unda geçerli JSON döndürdü (yalnız `K45_S11` sayfasında 1 kez JSON kesildi). Ayrıca model 135 adayın 11'inde `kitaptaki` ile `onerilen` alanını birebir aynı bıraktı (ör. `K42_A36` alıntı dizesinde `'hata olarak sayılmamıştır'` açıklaması yazarak). Ürün entegrasyonunda `norm(kitaptaki) == norm(onerilen)` olan çıktılar tek satırlık mekanik süzgeçle elenebilir; bu süzgeç uygulandığında aday sayısı 135'ten 124'e (2,07/sayfa), eşleşmeyen aday sayısı 115'ten 105'e (1,75/sayfa) düşmekte ve 18/44 gerçek hata (11 ek hata) korunmaktadır.

---

## 7. Sınırlamalar

- **Görülmüş sayfalar (Tarama niteliği):** Bu çalışma bir ürün ölçümü değil, araç taramasıdır. K42 ve K45'teki 60 sayfa önceki geliştirmelerde görülmüştür. Geçen aracın (`gemma4:12b-it-qat` ile temiz blok metni okuma) gerçek isabet ve bulma oranı, ürüne eklendikten sonra **daha önce hiç görülmemiş yeni bir kitapta** bağımsız 3 modelli kurulla ölçülecektir.
- **Eşleşmeyen işaretlerin niteliği:** Eşleşmeyen işaretlerin (`gemma4:12b-it-qat` için sayfa başına 1,92 adet) bir kısmı 3 modelli kurulun A taramasında işaretlemediği gerçek noktalama/yazım hataları veya stil önerileri olabilir; ancak bağımsız kurul oyu olmadığı için bu taramada tamamı muhafazakâr biçimde 'eşleşmeyen işaret' olarak sayılmıştır.
- **Çalışma süresi:** `gemma4:12b-it-qat` ile sayfa okuma sayfa başına ortalama 15,21 sn (300 sayfalık kitap için ~76 dk) sürmektedir; bu nedenle ürüne eklenirken hızlı kural/morfoloji taramasından ayrı, isteğe bağlı veya arka plan (derin tarama) adımı olarak konumlandırılması uygundur.
