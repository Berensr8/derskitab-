# K44 Yazım ve Kesme İyileştirmeleri — Geliştirme Ölçümü Sonuçları

**Bu sayılar geliştirme verisidir; kurallar bu hatalara bakılarak yazıldı. Gerçek etki K45'te ölçülecek.**

---

## 1. Özet Tablo (Geliştirme Verisi — Şişkin)

| Ölçüt | K44 Öncesi (`8c7834a`) | K44 Sonrası | Açıklama |
|---|---|---|---|
| **K42 B İsabeti (Hakemli, gösterilen $\ge 0{,}5$)** | 7 / 25 (%28,0; %95 GA: %14,3–47,6) | **7 / 16 (%43,8; %95 GA: %23,1–66,8)** | 9 eski/ağız sahte tespiti (`B03, B16, B10, B06, B19, B24, B26, B29, B35`) `0,25`'e indi; 7 gerçek hatanın tamamı korundu |
| **K42 B İsabeti (Hakemsiz, gösterilen $\ge 0{,}5$)** | 5 / 29 (%17,2; %95 GA: %7,6–34,5) | **5 / 20 (%25,0; %95 GA: %11,2–46,9)** | Aynı 9 eski/ağız sahte tespiti `0,25`'e indi |
| **K42 A Bulma Oranı (Gösterilen $\ge 0{,}5$)** | 0 / 17 (%0,0; %95 GA: %0,0–18,4) | **9 / 17 (%52,9; %95 GA: %31,0–73,8)** | Bölüm 3'teki 9 kural 9 gerçek hatayı yakaladı |
| **K42 A Bulma Oranı (Gizliler dahil)** | 1 / 17 (%5,9) | **10 / 17 (%58,8)** | 9 gösterilen + `A36` (`’abesdir`, alıntı içinde `0,25`) |
| **K39 B İsabeti (Hakemsiz, 17 gerçek hata zemini)** | 7 / 19 (%36,8; %95 GA: %19,1–59,0) | **7 / 19 (%36,8; %95 GA: %19,1–59,0)** | K39 B'de gerçek hata kaybı 0 (hakemli: 5/17 $\rightarrow$ 5/17) |
| **K39 A Bulma Oranı (Hakemsiz, 17 gerçek basım hatası)** | 9 / 17 (%52,9; %95 GA: %31,0–73,8) | **9 / 17 (%52,9; %95 GA: %31,0–73,8)** | `biyoloji9` s. 114'teki 5 gerçek hata (`molekullerinin` x2, `gecirgen`, `gecişidir`, `yuksek`) korundu |
| **K34 Kesme Etiketleri (`testseti/kesme_etiketler.json`)** | Ham kural: 30 gerçek, 12 sahte (`%71,4`) | **Ham kural: 30 gerçek, 8 sahte (`%78,9`)** | 4 `'Meryemce’nin'` sahte tespiti kalktı; gerçek kayıp 0 (ipuçları dahil: 5 sahteden 1 sahteye indi) |
| **56 Hatalık Yapay Gerileme Seti (`yazim_hatalari.json` test)** | 55 / 56 (%98,2) | **55 / 56 (%98,2)** | Alt sınır ($\ge 55/56$) korundu |

---

## 2. Bölüm 1: Eski Metin Sayfası İpucu ve Alıntı Genişletmesi

### Ne Değişti?
1. **`kriterler/alinti.py`**:
   - **İki sütunlu alıntı ve imza (`yan_sutun`, `imza_mi`):** Sağ sütunun altında yer alan ve kaynak parantezi ikinci satırda sola taşan küçük puntolu imzalar (`turkdili10` s. 19 `"Anonim (haz.: Ahmet Bican Ercilasun...)"`) tanındı; sağ sütundaki imzalı şiir/metin ile aynı üst hizada (`y0`) ve aynı puntoda yer alan sol sütun (`turkdili10` s. 18–19 Kırım Tatar Türkçesi dörtlükleri) alıntı bölgesine dahil edildi.
   - **Replik sayfasındaki ara dizeler (`replik_bloklari`):** Replikli tiyatro/Karagöz sayfalarında ilk ve son replik arasında aynı sütunda kalan şarkı/gazel dizeleri (`turkdili11` s. 19 Karagöz mukaddimesindeki `'üzre'`) alıntı sayıldı; sağ kenar kutuları (`Bilgi Köşesi`) ve numaralı soru başlıkları hariç tutuldu.
2. **`kriterler/dusuk_oncelik.py` (`eski_metin_sayfasi`)**:
   - PDF okuma parçası, terim ve alıntı ipuçları uygulandıktan sonra bir sayfada hâlâ **en az 4 farklı** `"iki araç da tanımadı"` morfoloji kelimesi kalmışsa (ör. `turkdili11` s. 156 Orhun Abideleri tablosu), o sayfadaki işaretsiz morfoloji ve kesme tespitleri `"Eski metin sayfası"` notuyla `0,25` güvene indirilir.
   - **Yakın kelime istisnası:** Kitapta geçen geçerli bir kelimeye tek harf/hece uzaklıkta olan gerçek yazım hataları (`yazim_hakem.yakin_dogru_kelime`, ör. `biyoloji9` s. 114 `'molekullerinin'`, `'gecirgen'`, `'gecişidir'`, `'yuksek'`) hem sayfa sayımından hem de düşürmeden muaftır.
   - **Günümüz Türkçesi koruması:** Aynı sayfada tek başına `"Günümüz Türkçesiyle"` başlığının altında kalan günümüz Türkçesi blokları (`turkdili12` s. 247 `'Tarkan’lar'`) düşürülmez.

### Kabul Ölçütü ve Kitap Başına Eski Metin Sayfaları
- **K42 B'deki 9 eski/ağız sahte tespiti:** 9/9'u `0,25` güvene indi (`B03 'yoğruşur'` ve `B16 'hoplaşır'` `turkdili10` s. 19 alıntı; `B10 'üzre'` `turkdili11` s. 19 alıntı; `B06 'tutsıkıngındevlet'`, `B19 'budunuğ'`, `B24 'yitü'`, `B26 'törüsin'`, `B29 'kılbirleşik'`, `B35 'bolsar'` `turkdili11` s. 156 eski metin sayfası).
- **Gerçek hata kaybı:** K42 B'deki 7 gerçek hatadan (`B01, B07, B22, B30, B34, B37, B38`) ve K39 `biyoloji9` s. 114'teki 5 gerçek hatadan hiçbiri düşmedi (kayıp: **0**).
- **Kitap başına `eski_metin_sayfasi` işaretlenen sayfalar:**
  - `kitap` (Sosyal 6): 0 sayfa
  - `matematik11`: 0 sayfa
  - `turkdili9`: 4 sayfa (`s. 176, 179, 192, 275`)
  - `turkdili10`: 4 sayfa (`s. 10, 68, 152, 179`; ayrıca `s. 18–19` doğrudan `alinti` ile yakalandı)
  - `turkdili11`: 5 sayfa (`s. 50, 98, 127, 156, 159`; ayrıca `s. 19` doğrudan `alinti` ile yakalandı)
  - `turkdili12`: 3 sayfa (`s. 222, 226, 247`)
  - `biyoloji9`: 6 sayfa (`s. 70, 72, 109, 130, 134, 144` — hakemden önce yoğun kimyasal/taksonomik tablo sayfaları; `s. 114` yakın kelime istisnasıyla korundu)
  - `biyoloji10`: 3 sayfa (`s. 52, 60, 68`)
  - `biyoloji11`: 3 sayfa (`s. 60, 233, 236`)

---

## 3. Bölüm 2: Öncelik Sırası Düzeltmesi

### Ne Değişti?
- `buyuk_harf_i` (`yazim.py`) güveni `0,5` $\rightarrow$ **`1,0`** yapıldı.
- Hakem `"doğru"` dese de kitaptaki geçerli bir kelimeye tek harf/hece uzak olan morfoloji tespitlerinin (`yazim_hakem.py` `yakin_dogru_kelime`) güveni `0,5` $\rightarrow$ **`1,0`** yapıldı.
- İki aracın da tanımadığı ham morfoloji tespitlerinin (`yazim.py` `kelime_denetimi`) başlangıç güveni `1,0` $\rightarrow$ **`0,75`** yapıldı.
- Arayüzde (`arayuz/ozet.py` `oncelik`) `"yüksek"` (`"öncelikli"`) eşiği $\ge 0{,}75$ olarak korundu; sıralama `guven_skoru` azalan sırada yapıldığı için artık en üstte `1,0` grubu (`buyuk_harf_i`, yakın kelime morfolojisi ve kesin TDK kuralları), hemen altında `0,75` grubu yer alıyor.

### K42 B Güven Grubu Tablosu (Geliştirme Verisi — Grup Başına $n = 1\text{–}17$, Çok Küçük Örneklem)

| Güven Grubu | K42 Eski Sıra (25 gösterilen) | Yalnız Bölüm 2 Yeni Sıra (25 gösterilen) | Bölüm 1 + Bölüm 2 Sonrası (16 gösterilen) |
|---|---|---|---|
| **1,0** | 1 / 10 (%10,0) | **5 / 7 (%71,4)** | **5 / 7 (%71,4)** |
| **0,75** | 1 / 8 (%12,5) | **2 / 17 (%11,8)** | **2 / 8 (%25,0)** |
| **0,5** | 5 / 7 (%71,4) | **0 / 1 (%0,0)** | **0 / 1 (%0,0)** |
| **Gösterilen Toplam ($\ge 0{,}5$)** | **7 / 25 (%28,0)** | **7 / 25 (%28,0)** | **7 / 16 (%43,8)** |
| **0,25 (Gizli)** | 0 / 13 (%0,0) | 0 / 13 (%0,0) | **0 / 22 (%0,0)** |

> **Not:** Güven gruplarındaki örneklem büyüklükleri çok küçüktür (grup başına 1–17 tespit); bu tablo geliştirme verisi üzerindedir.

---

## 4. Bölüm 3: Dokuz Küçük Kural

### 8 Kitapta (ve Sosyal 6 Dahil 9 Kitapta) Tespit Sayıları ve Tam Listesi

| # | `alt_tur` | Kural | Beklenen (Ön Deneme) | 8 Kitapta Bulunan | Tam Liste (Kitap, PDF Sayfası, Parça) |
|---|---|---|---|---|---|
| 1 | `bitisik_rakam` | Büyük harfle başlayan kelime + bitişik rakam (`Form11`) | 3 | **3** | `biyoloji9` s.76 `Form11`; `biyoloji9` s.123 `Form17`; `matematik11` s.86 `Tablo2` |
| 2 | `yil_virgul_bosluk` | İki yıl (1000–2100) arasında boşluksuz virgül (`1947,1962`) | 1 | **1** | `turkdili10` s.292 `1947,1962` |
| 3 | `liste_tutarsiz_virgul` | Sayı listesinde tutarsız virgül (`11,12, 13`; `%` hariç) | 1 (3 yüzde hariç) | **1** | `biyoloji9` s.155 `11,12, 13` |
| 4 | `iki_nokta_bosluk` | Kitapta $\ge 3$ kez ve $\ge 3\times$ boşluksuz yazılan büyük harfli kelimeden sonra boşluklu iki nokta (`Yönerge :`) | 5 | **5** | `biyoloji9` s.129 `Yönerge :`; s.143 `Yönerge :`; s.150 `Yönerge :`; s.178 `Belirlenmesi :`; s.181 `Belirlenmesi :` |
| 5 | `yonerge_cift_nokta` | Yönerge emir kipinden sonra çift nokta (`yazınız..`) | 2 fen (+1 TDE) | **3** | `biyoloji9` s.87 `yazınız..`; `biyoloji11` s.45 `Açıklayınız..`; `turkdili12` s.66 `belirtiniz..` |
| 6 | `yonerge_soru_isareti` | Yönerge emir kipinden sonra soru işareti (`veriniz?`) | 3 | **3** | `turkdili9` s.202 `söyleyiniz?`; `biyoloji11` s.158 `veriniz?`; `biyoloji11` s.219 `açıklayınız?` |
| 7 | `bir_takim` | `"bir takım"` + sonraki iki kelimeden biri çoğul (`-lar/-ler`) | 4 (7 geçişten) | **4** | `turkdili9` s.42 `bir takım`; `turkdili10` s.84 `bir takım`; `turkdili11` s.260 `bir takım`; `turkdili12` s.25 `bir takım` |
| 8 | `birim_gr` | Sayıdan sonra `"gr"` kısaltması (doğrusu `"g"`) | 2 | **2** | `turkdili10` s.68 `1283 gr`; `biyoloji11` s.235 `500 gr` |
| 9 | `yanlis_kelime` | Küçük TDK listesi (`coğrafik` $\rightarrow$ `coğrafi`) | 4 | **4** | `biyoloji9` s.142 `coğrafik`; s.148 `coğrafik`; s.149 `coğrafik`; `biyoloji10` s.133 `coğrafik` |
| **Toplam** | | | **25–26** | **26** | (`kitap` / Sosyal 6'da ek tespit: 0) |

### K42 A Sayfalarında Yakalanan Gerçek Hatalar (0/17 $\rightarrow$ 9/17 Gösterilen, 10/17 Gizli Dahil)
1. **`A02`** (`biyoloji9` s. 76): `'Form11'` $\rightarrow$ `bitisik_rakam` (`0,75`)
2. **`A05`** (`biyoloji9` s. 87): `'yazınız..'` $\rightarrow$ `yonerge_cift_nokta` (`0,75`)
3. **`A07`** (`biyoloji9` s. 142): `'coğrafik'` $\rightarrow$ `yanlis_kelime` (`0,75`)
4. **`A08`** (`biyoloji9` s. 150): `'Yönerge :'` $\rightarrow$ `iki_nokta_bosluk` (`0,75`)
5. **`A09`** (`biyoloji9` s. 155): `'11,12, 13'` $\rightarrow$ `liste_tutarsiz_virgul` (`0,75`)
6. **`A15`** (`biyoloji11` s. 158): `'örnek veriniz?'` $\rightarrow$ `yonerge_soru_isareti` (`0,75`)
7. **`A23`** (`turkdili10` s. 68): `'gr'` (`1283 gr`) $\rightarrow$ `birim_gr` (`0,75`)
8. **`A29`** (`turkdili10` s. 84): `'bir takım vasıflar'` $\rightarrow$ `bir_takim` (`0,75`)
9. **`A79`** (`turkdili10` s. 292): `'1947,1962'` $\rightarrow$ `yil_virgul_bosluk` (`0,75`)
- *(Gizli `0,25`)* **`A36`** (`turkdili10` s. 106): `'’abesdir'` $\rightarrow$ `morfoloji` (`0,25`, alıntı içinde)
- **Kaçırılan 7 gerçek hata:** `A04` (`Commasie`), `A10` (`Canis familaris`), `A11` (`Canidea`), `A14` (`akıllı termostatlar;`), `A17` (`Kap atışı`), `A18` (`solunum hızı;`), `A50` (`Sözlü alarak ifade ediniz.`).

---

## 5. Bölüm 4: Kesme İşareti (`testseti/kesme_etiketler.json`)

- **Kişi adı istisnası (`kesme.py`):** `-ca/-ce/-ça/-çe` ile biten kelime Zemberek sözlüğünde dil adı değilse (`not sozlukte_kendisi`) ve bilinen dil adları listesinde yer almıyorsa, kitapta özel ad olarak geçtiğinde (`Meryemce`) dil adı sayılmaz (`Meryemce’nin` x4 ve `Meryemce’yi` x1 elendi). Gerçek dil adları (`Türkçe’ye`, `Fransızca’dan`, `Uygurca’da`, `Almanca'da`, `Arapça'dan`) korundu.
- **`testseti/kesme_etiketler.json` (46 kural maddesi; 3 `'Ömerî'` K34 sonunda, 1 `'TÜRKÜLERIN'` PyMuPDF 1.28.2 blok farkında):
  - **Ham `kesme.py` kuralı (K34 ölçüm yöntemi):**
    - Önce: **30 gerçek, 12 sahte** (`30/42 = %71,4`)
    - Sonra: **30 gerçek, 8 sahte** (`30/38 = %78,9`) — **4 sahte (`Meryemce’nin` x4) düştü, gerçek kayıp 0**.
  - **Kitap ipuçları (`alinti` + `eski_metin_sayfasi`) dahil gösterilen ($\ge 0{,}5$):**
    - Kalan 8 sahtenin 7'si (`turkdili11` s. 110–111 `'Paşa’ların'` x3, `'Efendi’lerin'`, `'Şerîf’lere'`, `'Kerîm’lere'`, `'Bey’lerin'`) alıntı/eski metin ipucuyla `0,25`'e indi; geriye yalnız 1 sahte (`matematik11` s. 274 `'2dir'`) kaldı (`turkdili12` s. 247 `'Tarkan’lar'` ise `"Günümüz Türkçesiyle"` başlığı korumasıyla `0,5`'te korundu).

---

## 6. 8 Kitapta (ve 9 Kitapta) Toplam Yazım Tespiti Sayısı (Önce / Sonra)

### 8 Kitap (`biyoloji9, biyoloji10, biyoloji11, matematik11, turkdili9, turkdili10, turkdili11, turkdili12`)

| Mod | Güven Grubu | K44 Öncesi | K44 Sonrası | Fark |
|---|---|---|---|---|
| **Hakemli (Varsayılan)** | **1,0** | 323 | **163** | -160 |
| | **0,75** | 98 | **291** | +193 |
| | **0,5** | 114 | **29** | -85 |
| | **Gösterilen Toplam ($\ge 0{,}5$)** | **535** | **483** | **-52** |
| | **0,25 (Gizli)** | 2.272 | **2.345** | +73 |
| | **Genel Toplam** | 2.807 | **2.828** | +21 (+26 yeni kural, -5 `Meryemce`) |
| **Hakemsiz** | **1,0** | 757 | **99** | -658 |
| | **0,75** | 0 | **524** | +524 |
| | **0,5** | 50 | **29** | -21 |
| | **Gösterilen Toplam ($\ge 0{,}5$)** | **807** | **652** | **-155** |
| | **0,25 (Gizli)** | 2.000 | **2.176** | +176 |
| | **Genel Toplam** | 2.807 | **2.828** | +21 |

### 9 Kitap (`kitap` / Sosyal Bilgiler 6 Dahil)

| Mod | Güven Grubu | K44 Öncesi | K44 Sonrası | Fark |
|---|---|---|---|---|
| **Hakemli (Varsayılan)** | **1,0** | 350 | **263** | -87 |
| | **0,75** | 102 | **312** | +210 |
| | **0,5** | 220 | **45** | -175 |
| | **Gösterilen Toplam ($\ge 0{,}5$)** | **672** | **620** | **-52** |
| | **0,25 (Gizli)** | 2.314 | **2.387** | +73 |
| | **Genel Toplam** | 2.986 | **3.007** | +21 |
| **Hakemsiz** | **1,0** | 795 | **197** | -598 |
| | **0,75** | 0 | **552** | +552 |
| | **0,5** | 154 | **45** | -109 |
| | **Gösterilen Toplam ($\ge 0{,}5$)** | **949** | **794** | **-155** |
| | **0,25 (Gizli)** | 2.037 | **2.213** | +176 |
| | **Genel Toplam** | 2.986 | **3.007** | +21 |
