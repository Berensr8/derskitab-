# Bağımsız değerlendirme 3: yeni kitaplarda K44'ün gerçek etkisi (K45, 2026-11-15)

**Neden:** K44 yazım iyileştirmeleri (commit `ba44473`), geliştirme verisinde (K42'nin A ve B sayfalarında) hakemli isabeti 7/25'ten (%28,0) 7/16'ya (%43,8), gösterilen bulma oranını ise 0/17'den (%0,0) 9/17'ye (%52,9) çıkarmıştı. Ancak K44 kuralları doğrudan K42'de kaçan hatalara ve yanlış alarmlara bakılarak yazıldığı için geliştirme verisindeki bu artış iyimserdir (aşırı uyum / veri sızıntısı). Bu çalışma (K45), dondurulmuş `ba44473` ürün kodunu geliştirme sürecinde **hiç kullanılmamış iki yeni ders kitabında** (`biyoloji12` ve `inkilap12`) K42 ile birebir aynı bağımsız kurul yöntemiyle sınamaktadır.

Ön kayıt belgesi: `testseti/k45_on_kayit.md` (commit `51f0ed2`). Sistemin kilitli çıktıları ve parmak izleri kurul oylamasından önce kilitlendi (`testseti/bagimsiz3_kilit.txt`, commit `f870cc2` ve `1a8ddf0`).

---

## Ön Kayıt Başarı Ölçütleri Karşılama Tablosu

| No | Ön Kayıt Ölçütü | Hedef | Gerçekleşen | Durum |
|---|---|---|---|:---:|
| 1 | Hakemli B İsabeti (Kurul çoğunluk oyu $\ge$ 2/3) | $\ge$ %35 | 20/76 = **%26,3** (%17,7–%37,2) | **✗** |
| 2 | A Bulma Oranı (Gösterilen tespitler, güven $\ge$ 0,5) | $\ge$ %30 | 1/27 = **%3,7** (%0,7–%18,3) | **✗** |
| 3 | Öncelik Sırası Ters Değil (`güven = 1,0` isabeti $\ge$ `güven = 0,75` isabeti) | %1,0 $\ge$ %0,75 | `1,0`: 4/35 = **%11,4** < `0,75`: 11/34 = **%32,4** (`0,5`: 5/7 = **%71,4**) | **✗** |
| 4 | K44 Kurallarında İsabet (En az 3 tespiti olan her kuralda $\ge$ %50) | $\ge$ %50 | En az 3 tespiti olan tek K44 kuralı `bitisik_rakam`: **0/4 = %0,0** (4'ü de `Cas9`); `yonerge_soru_isareti`: 2/2 (%100, <3 tespit); diğer 7 K44 kuralında 0 tespit | **✗ (`bitisik_rakam` işaretlendi)** |

- **Özet karar:** Ön kayıtta belirlenen dört başarı ölçütünün hiçbiri yeni kitaplarda sağlanamamıştır. Geliştirme verisinde (K44) görülen yüksek sıçrama (isabet %43,8; bulma %52,9), görülmemiş yeni kitaplara genelleşmemiştir.

---

## Yöntem ve Kilitli Örneklem

- **Yeni kitaplar:**
  - `veri/biyoloji12.pdf` (Biyoloji 12, 213 sayfa, 210 metinli sayfa, 6.206 blok; SHA-256 ilk 16: `1f0a78b8d035d330`).
  - `veri/inkilap12.pdf` (T.C. İnkılâp Tarihi ve Atatürkçülük 12, 287 sayfa, 281 metinli sayfa, 5.108 blok; SHA-256 ilk 16: `64a392e28af85a93`).
- **Ölçülen sistem:** Dondurulmuş `ba44473` sürümü (`.venv` Python 3.11, PyMuPDF `1.28.2`). Ürünün varsayılan yapılandırması: yazım hakemi açık (`Ollama` + `gemma4:12b-it-qat`). Hakemsiz çıktı ikincil olarak ayrıca hesaplanmıştır.
- **A, bulma oranı (30 kilitli sayfa, tohum `20261116`):**
  - İlk ve son 10 sayfa hariç, en az 150 kelime paragraf içeren uygun sayfalar arasından kitap başına 15'er sayfa (`S01`–`S15`: Biyoloji 12; `S16`–`S30`: İnkılâp 12).
  - ChatGPT (`gpt.txt`, 35 satır) ve Gemini (`gemini.txt`, 58 satır) bu sayfaları sistemden bağımsız okuyarak yazım ve noktalama hatalarını çıkardı (`A_talimat.txt`).
  - İki modelin bulguları birleştirildi: önerilen biçimi kitapta zaten mevcut olan veya modelin "TDK doğru" notu düştüğü 12 dayanaksız madde elendi (`ATLANAN`); toplam **68 benzersiz A adayı** (`A01`–`A68`) oluştu (`gemini`: 33, `chatgpt`: 20, `chatgpt+gemini`: 15). Mekanik metin katmanı kontrolünde (`k42_katman.py`) A adaylarında katman farkı çıkmadı (`0`).
- **B, isabet (A dışındaki bütün sayfalar = 470 sayfa):**
  - İki kitabın A dışındaki tüm sayfalarında (`biyoloji12`: 198 sayfa, `inkilap12`: 272 sayfa) gösterilen (`güven ≥ 0,5`) benzersiz tespit sayısı hakemli sistemde **133**, hakemsiz sistemde **205** oldu.
  - Ön kayıt kuralı gereği 80'den fazla olduğu için `20261116` tohumuyla hakemli sistemden **80**, hakemsiz sistemden **80** rastgele tespit seçildi (28'i ortak).
  - Ayrıca K44'ün 9 kuralı ve `buyuk_harf_i` için B sayfalarındaki tüm gösterilen tespitler (kural başına en çok 10) eklendi (`bitisik_rakam`: 4, `yonerge_soru_isareti`: 2, `buyuk_harf_i`: 4; 80 örneklemi dışından eklenen 1 adet `bitisik_rakam` ile birleşik B listesi **133** aday oldu).
  - **Metin katmanı kontrolü (K41-ek):** Hakemli 80 örneklem içinde yer alan 4 adet `buyuk_harf_i` tespiti (`B02: POLITIK`, `B09: SIYASİ`, `B44: POLITIKASI`, `B108: DEKI` — tümü `inkilap12` s. 10–11 içindekiler sayfasında InDesign `ActualText` kaynaklı sahte I/İ farkı) mekanik glif kontrolüyle yakalanarak kurula gönderilmedi ve pay/paydadan çıkarıldı. Böylece kurulda değerlendirilen B örneklem büyüklüğü hakemlide **76**, hakemsizde **80**, birleşik B listesinde **129** oldu.
- **Karar kurulu:**
  - Toplam **197 aday** (A'dan 68, B'den 129), tohum `20261116` ile karıştırılarak nötr kimliklerle (`K001`–`K197`) ChatGPT, Gemini ve DeepSeek'e sunuldu (`KURUL_talimat.txt`).
  - Karar kuralı: en az 2/3 çoğunluk oyu (`HATA`, `DEGIL`, aksi halde `BELIRSIZ`).

---

## Sonuçlar

### 1. İsabet: sistemin gösterdiklerinin kaçı gerçek hata? (B)

| Yapılandırma / Ölçü | K45 Sonucu (%95 Wilson aralığı) | K42 Sonucu (Karşılaştırma) | K44 Geliştirme Verisi |
|---|---|---|---|
| **Hakemli (Ürün varsayılanı — Ana Sonuç)** | **20/76 = %26,3** (%17,7–%37,2) | 7/25 = %28,0 (%14,3–%47,6) | 7/16 = %43,8 (%23,1–%66,8) |
| Oybirliği (3/3 model "HATA") | 12/76 = %15,8 (%9,3–%25,6) | 5/25 = %20,0 (%8,9–%39,1) | - |
| En az bir model "HATA" dedi | 41/76 = %53,9 (%42,8–%64,7) | 11/25 = %44,0 (%26,7–%62,9) | - |
| **Hakemsiz (İkincil Sonuç)** | **12/80 = %15,0** (%8,8–%24,4) | 5/29 = %17,2 (%7,6–%34,5) | 5/20 = %25,0 (%11,2–%46,9) |

- **Hakem etkisinin değerlendirilmesi:**
  - Hakemli isabet **%26,3** (%17,7–%37,2), hakemsiz isabet **%15,0** (%8,8–%24,4) çıkmıştır (güven aralıkları kısmen çakışmaktadır).
  - Hakemsiz 80 örneklem içinde gösterilip hakem tarafından düşük önceliğe (`< 0,5`) indirilerek gizlenen **35 tespitin 34'ü (%97,1)** kurul tarafından `DEGIL` ("HATA DEĞİL") olarak oylanmıştır; yalnızca 1 tanesi (`B42: fosfolipid`, 2/3 oyla `HATA`) gizlenmiştir.
  - Buna karşılık hakemli 76 örneklem içinde, hakemsizde düşük öncelikte (`0,25`) olup hakem veya `yakin_dogru_kelime` tarafından `≥ 0,5`'e yükseltilen **14 tespitin 14'ü de (`0/14`)** kurulca `DEGIL` sayılmıştır (`bloka`, `mevzuu`, `arşa`, `more`, `demiryol`, `medâr`, `fotonlarındaki`, `over`, `şehid`, `çiftli`, `yalapa`, `fene`).
- **Kitap başına isabet:**
  - **Biyoloji 12:** Hakemli **14/56 = %25,0** (%15,5–%37,7); Hakemsiz **9/71 = %12,7** (%6,8–%22,4).
  - **T.C. İnkılâp Tarihi ve Atatürkçülük 12:** Hakemli **6/20 = %30,0** (%14,5–%51,9) *(+4 katman farkı hariç)*; Hakemsiz **3/9 = %33,3** (%12,1–%64,6).
- **Hakemli sistemin B örnekleminde yakaladığı 20 gerçek hata:**
  1. `asiti` (`biyoloji12` s. 40, `morfoloji`, güven 0,75) — Ünsüz yumuşaması eksikliği (doğrusu: *asidi*).
  2. `olduğudan` (`biyoloji12` s. 46, `morfoloji`, güven 0,75) — Harf eksikliği (doğrusu: *olduğundan*).
  3. `kulanılır` (`biyoloji12` s. 57, `morfoloji`, güven 0,75) — Eksik ünsüz (doğrusu: *kullanılır*).
  4. `yazınız?` (`biyoloji12` s. 91, `yonerge_soru_isareti`, güven 0,75) — Emir kipinden sonra soru işareti (doğrusu: *yazınız.*).
  5. `cevaplayınız?` (`biyoloji12` s. 98, `yonerge_soru_isareti`, güven 0,75) — Emir kipinden sonra soru işareti (doğrusu: *cevaplayınız.*).
  6. `dinükleotid` (`biyoloji12` s. 102, `morfoloji`, güven 0,75) — Terim sonunda *d/t* uyumsuzluğu (doğrusu: *dinükleotit*).
  7. `tomucuklarının` (`biyoloji12` s. 142, `morfoloji`, güven 0,75) — Harf eksikliği (doğrusu: *tomurcuklarının*).
  8. `kleoptil` (`biyoloji12` s. 153, blok 7, `morfoloji`, güven 0,75) — Harf eksikliği (doğrusu: *koleoptil*).
  9. `kleoptil` (`biyoloji12` s. 153, blok 14, `morfoloji`, güven 0,75) — Harf eksikliği (doğrusu: *koleoptil*).
  10. `ozmazla` (`biyoloji12` s. 163, `morfoloji`, güven 0,75) — Yanlış ünlü (doğrusu: *ozmozla*).
  11. `ve ve` (`biyoloji12` s. 174, `kelime_tekrari`, güven 1,0) — Bağlaç tekrarı.
  12. `sağlar. (Görsel 3.104).` (`biyoloji12` s. 180, `noktalama_parantez_cift_nokta`, güven 1,0) — Parantezli göndermede çift nokta.
  13. `yada` (`biyoloji12` s. 199, `ya_da`, güven 0,5) — Bitişik yazılan *ya da* bağlacı.
  14. `plâzmit` (`biyoloji12` s. 209, `morfoloji`, güven 0,75) — Gereksiz düzeltme işareti (doğrusu: *plazmit*).
  15. `erlendirildi.Gelişmelerin` (`inkilap12` s. 22, `noktalama_bosluk`, güven 1,0) — Noktadan sonra boşluk eksikliği.
  16. `Jean De` (`inkilap12` s. 33, `bag_de_da_uyum`, güven 1,0) — Yabancı özel adda büyük *De* (sistem bağlaç kuralıyla işaretledi, kurul büyük harf hatası saydı).
  17. `İngilizler'e` (`inkilap12` s. 94, `gereksiz_kesme`, güven 0,5) — Çokluk ekinden sonra kesme işareti.
  18. `önayak oldu.(...)` (`inkilap12` s. 157, `noktalama_bosluk`, güven 0,5) — Noktadan sonra boşluk eksikliği.
  19. `İngilizler’e` (`inkilap12` s. 230, `gereksiz_kesme`, güven 0,5) — Çokluk ekinden sonra kesme işareti.
  20. `yada` (`inkilap12` s. 281, `ya_da`, güven 0,5) — Bitişik yazılan *ya da* bağlacı.

---

### 2. Güven Düzeyi Sırası (Ölçüt 3: Ters Sıralama Devam Ediyor)

K44'te güven puanları yeniden düzenlenmiş (`yakin_dogru_kelime` ve `buyuk_harf_i` $\rightarrow 1,0$; iki aracın uzlaştığı morfoloji $\rightarrow 0,75$) ve geliştirme verisinde sıralama düzelmiş görünmüştü (`1,0`: 5/7 = %71,4; `0,75`: 2/8 = %25,0). Ancak yeni kitaplarda sıralama yeniden tersine dönmüştür:

| Güven Skoru | Arayüzdeki Öncelik | Hakemli B Tespit Sayısı | Kurulun HATA Dediği | Hakemli İsabet Oranı | Hakemsiz İsabet Oranı |
|---|---|---:|---:|---|---|
| **1,0** | "Öncelikli" | 35 | 4 | **4/35 = %11,4** (%4,5–%25,9) | 2/4 = %50,0 |
| **0,75** | "Kontrol edilecek" | 34 | 11 | **11/34 = %32,4** (%19,1–%49,2) | 9/74 = %12,2 |
| **0,5** | "Kontrol edilecek" | 7 | 5 | **5/7 = %71,4** (%35,9–%91,8) | 1/2 = %50,0 |

- **Neden `güven = 1,0` grubunda isabet %11,4'e düştü?**
  - `güven = 1,0` grubundaki 35 tespitin **30'u**, yerel dil modelinin (`gemma4`) aslında **"DOĞRU"** dediği, ancak `yakin_dogru_kelime` mekanizmasının (kitapta 1 harf uzağında başka bir kelime geçtiği için) hakem kararını ezerek `1,0` puana yükselttiği tespitlerdir:
    - Biyoloji 12'de geçen **`mRNA` (14 kez), `tRNA` (6 kez), `rRNA` (3 kez)** kısaltmaları (toplam **23 tespit**), kitapta `RNA` kelimesi geçtiği için `RNA`'ya 1 harf uzaklıkta sayılmış ve `gemma4` "uluslararası standart kısaltmadır, doğrudur" demesine rağmen `yakin_dogru_kelime` tarafından `1,0` ("Öncelikli") yapılmıştır.
    - Benzer şekilde `bloka` (2 kez, `blokla`'ya yakın), `mevzuu` (2 kez, `mevzu`'ya yakın), `porlar` (`polar`'a yakın), `arşa` (`ara`'ya yakın) ve `vaz’iyetin` (`vaziyetin`'e yakın) kelimeleri de `yakin_dogru_kelime` tarafından `1,0`'a taşınmıştır (tümü kurulca `DEGIL`).
  - Buna karşılık `gemma4`'ün gerçekten "HATA" dediği morfoloji tespitleri (`asiti`, `olduğudan`, `kulanılır`, `tomucuklarının`, `kleoptil`, `ozmazla`, `dinükleotid`, `plâzmit`) K44'teki değişiklikle `0,75` puanda kaldığı için `0,75` grubunun isabeti (%32,4), `1,0` grubunun (%11,4) üstüne çıkmıştır.

---

### 3. Kural Başına İsabet (Ölçüt 4: K44 Kuralları ve Diğer Kurallar)

| Kural (`alt_tur`) | Kaynak | B Kurulda Değerlendirilen | Kurulun HATA Dediği | Katman Farkı (Kurul Dışı) | İsabet | Ölçüt 4 Durumu |
|---|---|---:|---:|---:|---|---|
| `bitisik_rakam` | K44 | 4 | 0 | 0 | **0/4 = %0,0** | **✗ (< %50, işaretlendi)** |
| `yonerge_soru_isareti` | K44 | 2 | 2 | 0 | **2/2 = %100,0** | < 3 tespit (`yazınız?`, `cevaplayınız?`) |
| `yil_virgul_bosluk` | K44 | 0 | - | 0 | - | Havuzda tespit yok |
| `liste_tutarsiz_virgul` | K44 | 0 | - | 0 | - | Havuzda tespit yok |
| `iki_nokta_bosluk` | K44 | 0 | - | 0 | - | Havuzda tespit yok |
| `yonerge_cift_nokta` | K44 | 0 | - | 0 | - | Havuzda tespit yok |
| `bir_takim` | K44 | 0 | - | 0 | - | Havuzda tespit yok |
| `birim_gr` | K44 | 0 | - | 0 | - | Havuzda tespit yok |
| `yanlis_kelime` | K44 | 0 | - | 0 | - | Havuzda tespit yok |
| `buyuk_harf_i` | K41 | 0 | - | 4 | - | 4 tespitin 4'ü de katman farkı (`inkilap12` s. 10–11) |
| `noktalama_parantez_cift_nokta` | K41 | 1 | 1 | 0 | **1/1 = %100,0** | K41 kuralı (`sağlar. (Görsel 3.104).`) |
| `morfoloji` (Hakemli 80) | Temel | 59 | 9 | 0 | **9/59 = %15,3** | Birleşik B'de: 14/109 = %12,8 |
| `gereksiz_kesme` (Hakemli 80) | Temel | 3 | 2 | 0 | **2/3 = %66,7** | `İngilizler'e` (2), `Rumlar’a` (alıntı: DEGIL) |
| `noktalama_bosluk` (Hakemli 80) | Temel | 2 | 2 | 0 | **2/2 = %100,0** | Birleşik B'de: 3/3 = %100,0 |
| `ya_da` (Hakemli 80) | Temel | 2 | 2 | 0 | **2/2 = %100,0** | `yada` (2) |
| `kelime_tekrari` (Hakemli 80) | Temel | 1 | 1 | 0 | **1/1 = %100,0** | `ve ve` |
| `bag_de_da_uyum` (Hakemli 80) | Temel | 1 | 1 | 0 | **1/1 = %100,0** | Birleşik B'de: 1/2 = %50,0 |
| `ozel_ad_kesme` (Hakemli 80) | Temel | 1 | 0 | 0 | **0/1 = %0,0** | `Milletler Cemiyetinden` (kurum adı: DEGIL) |
| `soru_eki_uyum` (Hakemli 80) | Temel | 1 | 0 | 0 | **0/1 = %0,0** | `genel müdür` (yanlış alarm) |

- **İşaretlenen K44 kuralı (`bitisik_rakam`):** Biyoloji 12'de 4 kez geçen **`Cas9`** (CRISPR-Cas9 sistemi enzim adı) `[A-Za-zÇĞİÖŞÜçğıöşü]{3,}\d+` desenine takılarak "kelimeye bitişik rakam" olarak işaretlenmiştir; kurulun üç üyesi de 4'üne de `HATA DEĞİL` demiştir (**0/4 = %0,0**). Biyoloji ve kimya metinlerinde `Cas9`, `p53`, `VitB12` gibi kısaltma/protein adları yaygın olduğundan kural bu haliyle yüksek yanlış alarm üretmektedir.
- **`buyuk_harf_i` ve katman farkı gözlemi:** `inkilap12` s. 10 ve 11'deki içindekiler tablosunda yer alan `POLITIK`, `SIYASİ`, `POLITIKASI`, `DEKI` kelimeleri PDF'te InDesign `ActualText` katmanından kaynaklanmaktadır. `pdf_cikarma.py` içindeki `_i_duzelt` fonksiyonu satır içi noktalı liderler (`....`) nedeniyle `SequenceMatcher` blok eşleşmesinde bu 4 kelimeyi düzeltememiş, ancak K41-ek mekanik glif kontrolü (`katman_farki`) bunları yakalamıştır.

---

### 4. Bulma Oranı: sayfalardaki gerçek hataların kaçını buldu? (A)

- Bağımsız kurul, 30 kilitli A sayfasındaki 68 adaydan **27 tanesine "HATA"** dedi (`biyoloji12`: 17 hata, `inkilap12`: 10 hata).
- **Sonuç:**

| Kapsam | Gerçek Hata Sayısı | Sistemin Yakaladığı | Bulma Oranı (Recall) (%95 Wilson) |
|---|---:|---:|---|
| **Hakemli Gösterilen (Güven $\ge$ 0,5)** | 27 | 1 | **1/27 = %3,7** (%0,7–%18,3) |
| **Hakemsiz Gösterilen (Güven $\ge$ 0,5)** | 27 | 0 | **0/27 = %0,0** (%0,0–%12,5) |
| **Düşük Öncelikliler Dahil (Güven $\ge$ 0,25)** | 27 | 1 | **1/27 = %3,7** (%0,7–%18,3) |

- **Yakalanan tek hata (`1/27`):**
  - **A58 (`K168`, S25, `inkilap12` s. 179):** `kollektifleştirme` $\rightarrow$ `kolektifleştirme` (3/3 `HATA`). Hakemsiz çıktıda yalnızca bir morfolojik çözümleyici (Starlang) tanımadığı için `0,25` güven puanı almış, ancak yazım hakemi (`gemma4`) "TDK'ye göre tek l ile kolektifleştirme yazılır" diyerek güven puanını `0,75`'e yükselttiği için hakemli sistemde yakalanmıştır.
- **Kaçan 26 gerçek hatanın türlerine göre dökümü:**
  1. **Kesme işaretinden önce veya sonra boşluk bırakılması (5 hata):**
     - `A01` (S01): `1953’ te` $\rightarrow$ `1953’te`
     - `A04` (S02): `Görsel 1.8’ de` $\rightarrow$ `Görsel 1.8’de`
     - `A05` (S03): `Görsel 2.2 ‘de` $\rightarrow$ `Görsel 2.2’de`
     - `A14` (S07): `H2S’ dir` $\rightarrow$ `H2S’dir`
     - `A22` (S11): `%78’ i` $\rightarrow$ `%78’i`
  2. **Sözlükte tek başına geçerli kelime olan bağlamsal ek / çekim / dizgi hataları (5 hata):**
     - `A06` (S03): `tepkimelerine endergonik tepkimeler, enerji açığa çıkaran tepkimelerine ise` $\rightarrow$ `tepkimelere` (`tepkimelerine` sözlükte geçerli çekim).
     - `A20` (S10): `Yaprağının enine kesitinde` $\rightarrow$ `Yaprağın enine kesitinde` (`Yaprağının` geçerli çekim).
     - `A28` (S14): `Oksin hormonun` $\rightarrow$ `Oksin hormonunun` (`hormonun` geçerli çekim).
     - `A29` (S15): `işaretleyiz` $\rightarrow$ `işaretleyiniz` (Zemberek/Starlang `işaret-le-yiz` olarak çözümlediği için morfolojiden geçti).
     - `A53` (S22): `Büyük Millet Meclis` $\rightarrow$ `Büyük Millet Meclisi` (`Meclis` tek başına geçerli).
  3. **Cümle içi virgül / noktalı virgül ve noktalama boşluğu hataları (6 hata):**
     - `A02` (S01): `(Görsel 1.2)],1869` $\rightarrow$ `(Görsel 1.2)], 1869` (`noktalama_bosluk` köşeli parantez sonrası `,1869` dizisini sayı içi virgül istisnası nedeniyle atladı).
     - `A13` (S07): `gece gündüz fotosentezi` $\rightarrow$ `gece gündüz, fotosentezi` (eksik virgül).
     - `A19` (S10): `Kloroplast içermez bu yüzden` $\rightarrow$ `Kloroplast içermez, bu yüzden` (sıralı cümlede eksik virgül).
     - `A23` (S12): `Ksilemdeki su ,` $\rightarrow$ `Ksilemdeki su,` (virgülden önce boşluk).
     - `A39` (S20): `Kazım Karabekir;` $\rightarrow$ `Kazım Karabekir` (gereksiz noktalı virgül).
     - `A46` (S20): `riya tembellik` $\rightarrow$ `riya, tembellik` (eş görevli kelimeler arasında eksik virgül).
  4. **Kesme işareti ve özel ad / kısaltma eki hataları (4 hata):**
     - `A15` (S07): `O2 dir` $\rightarrow$ `O2’dir` (kimyasal formüle gelen ekte kesme eksikliği).
     - `A51` (S21): `Türkiye Cumhuriyetine` $\rightarrow$ `Türkiye Cumhuriyeti’ne` (devlet adına gelen ekte kesme eksikliği).
     - `A60` (S27): `Demokrat Parti (DP)’nin` $\rightarrow$ `Demokrat Partinin (DP)` (parantezli kısaltmada ek ve kesme kullanımı).
     - `A66` (S30): `Yarımada’yı` $\rightarrow$ `yarımadayı` (cins adında büyük harf ve kesme).
  5. **Kısaltma ve yabancı özel ad büyük/küçük harf veya harf hataları (3 hata):**
     - `A08` (S04): `Engelman deneyi` $\rightarrow$ `Engelmann deneyi` (yabancı özel ad).
     - `A63` (S29): `suv modeli` $\rightarrow$ `SUV modeli` (küçük harfli kısaltma).
     - `A64` (S29): `COVİD-19` $\rightarrow$ `COVID-19` (yabancı kısaltmada Türkçe `İ` harfi; `buyuk_harf_i` kuralı `I` $\rightarrow$ `İ` yönünü aradığı için ters yöndeki `İ` $\rightarrow$ `I` hatasını denetlemez).
  6. **Bulunma eki `-de`'nin ayrı yazılması (1 hata):**
     - `A24` (S12): `Ksilem de` $\rightarrow$ `Ksilemde` (sistem yalnızca bitişik yazılan bağlaçları ve ünlü uyumsuz ayrı `de/da`'ları denetler; bağlamca bulunma eki olması gereken ayrı `de`'yi yakalamaz).
  7. **Tabii / tabi karışıklığı (1 hata):**
     - `A52` (S22): `ve tabi bu arada` $\rightarrow$ `ve tabii bu arada` (`tabi` tek başına "bağımlı" anlamında geçerli sözcük olduğu için sözlükten geçer).
  8. **Tablo başlığında büyük/küçük harf tutarsızlığı (1 hata):**
     - `A17` (S07): `Farklı yönleri` $\rightarrow$ `Farklı Yönleri`.

---

### 5. Kurulun Kendi İçindeki Uyumu

- **İkili ham uyum (197 aday üzerinden):**
  - ChatGPT – Gemini: **%86,3**
  - ChatGPT – DeepSeek: **%70,6**
  - Gemini – DeepSeek: **%66,0**
- **Üçünün de aynı oyu verdiği aday:** 121 / 197 (**%61,4**).
- **Fleiss κ:** **0,425** (Orta düzey uyum; K39: 0,33, K42: 0,471).

---

### 6. K42, K44 (Geliştirme) ve K45 (Yeni Kitaplar) Yan Yana Karşılaştırması

| Boyut | K42 Bağımsız Değerlendirme 2 (5 Eski Kitap) | K44 Geliştirme Verisi (K42 Sayfalarında) | K45 Bağımsız Değerlendirme 3 (2 Yeni Kitap) | Yorum |
|---|---|---|---|---|
| **B İsabeti (Hakemli)** | 7/25 = **%28,0** (%14,3–%47,6) | 7/16 = **%43,8** (%23,1–%66,8) | **20/76 = %26,3** (%17,7–%37,2) | Yeni kitaplarda hakemli isabet K42 düzeyiyle (%26–28) aynı kaldı |
| **B İsabeti (Hakemsiz)** | 5/29 = **%17,2** (%7,6–%34,5) | 5/20 = **%25,0** (%11,2–%46,9) | **12/80 = %15,0** (%8,8–%24,4) | Hakemsiz isabet %15–17 bandında sabit |
| **Hakemin Gizlediği Tespitler** | 13/13 = %100,0 `DEGIL` | 13/13 = %100,0 `DEGIL` | **34/35 = %97,1 `DEGIL`** (yalnız 1 `HATA`: `fosfolipid`) | Hakemin yanlış alarm eleme başarısı yeni kitaplarda da doğrulandı |
| **A Bulma Oranı (Gösterilen)** | 0/17 = **%0,0** (%0,0–%18,4) | 9/17 = **%52,9** (%31,0–%73,8) | **1/27 = %3,7** (%0,7–%18,3) | K44'teki 9 dar noktalama/kelime kuralı yeni kitaplardaki A hatalarına denk gelmedi |
| **A Bulma Oranı (Gizliler Dahil)** | 1/17 = **%5,9** (%0,3–%26,9) | 10/17 = **%58,8** | **1/27 = %3,7** (%0,7–%18,3) | A58 `kollektifleştirme` hakem desteğiyle yakalandı |
| **Güven Sıralaması (`1,0` / `0,75` / `0,5`)** | %10,0 / %12,5 / %71,4 (Ters) | %71,4 / %25,0 / %0,0 (Düz) | **%11,4 / %32,4 / %71,4 (Ters)** | `yakin_dogru_kelime` (`mRNA`/`tRNA`/`rRNA`) `1,0` grubunu yanlış alarmla doldurdu |
| **Kurul Uyumu (Fleiss κ)** | 0,471 | - | **0,425** | Orta düzey uyum korundu |

---

## Sınırlılıklar

1. **Ders ve kitap farkı:** K42 beş kitapta (Biyoloji 9, Biyoloji 11, TDE 10, TDE 11, TDE 12) ölçülmüştü; K45 ise daha önce hiç kullanılmamış **Biyoloji 12** ve **T.C. İnkılâp Tarihi ve Atatürkçülük 12** kitaplarında yapıldı. TDE kitaplarının yerini İnkılâp Tarihi kitabının alması metin türlerini (şiir/halk edebiyatı yerine tarihî belgeler, Misak-ı İktisadi kararları, kurum ve antlaşma adları) değiştirmiştir; bu nedenle K42 ile K45 arasındaki karşılaştırma birebir aynı dağılım üzerinde değildir.
2. **Kurul insan uzman değil:** Oylama üç büyük dil modelinin (ChatGPT, Gemini, DeepSeek) 2/3 çoğunluk oyuyla yapılmıştır ($\kappa = 0,425$). Dil modelleri özellikle kurum adlarına gelen kesme işaretlerinde ve bilimsel terimlerin sonunda *d/t* yazımında (`dinükleotid`, `fosfolipid`) kendi aralarında zaman zaman ayrışabilmektedir.
3. **Bulma oranı (recall) paydası bir üst sınırdır:** A sayfalarındaki gerçek hata havuzu ChatGPT ve Gemini'nin bağımsız okumada fark ettiği adaylarla sınırlıdır; iki modelin de gözünden kaçan hatalar paydada yer almaz.
4. **Dar kural tabanlı iyileştirmelerin yapısal sınırı:** K44'te eklenen 9 kural, K42 A sayfalarındaki spesifik hataları (`Form11`, `11,12, 13`, `Yönerge :`, `yazınız..`, `bir takım`, `gr`, `coğrafik`) hedeflemişti. Yeni kitaplarda ise A sayfalarındaki hataların önemli bir kısmı kesme işareti etrafındaki boşluklardan (`1953’ te`, `Görsel 1.8’ de`, `%78’ i`), cümle içi virgül eksikliklerinden ve sözlükte tek başına geçerli olan yanlış çekimli kelimelerden (`Yaprağının`, `hormonun`, `işaretleyiz`, `Meclis`) oluştuğu için dar kurallar bulma oranını anlamlı ölçüde artıramamıştır.

---

## Dosyalar ve Parmak İzleri

- Ön kayıt belgesi: `testseti/k45_on_kayit.md`
- Kilit dosyası: `testseti/bagimsiz3_kilit.txt`
- Kurul sonuçları: `veri/bagimsiz3/kurul_sonuc.json`
- Ham oylar: `bagimsiz_degerlendirme3/KURUL_GPT.txt`, `KURUL_GEMİNİ.txt`, `KURUL_DP.txt` (`A` okumaları: `gpt.txt`, `gemini.txt`)
- Anahtarlar: `veri/bagimsiz3/havuz.json`, `kurul_anahtar.json`, `A_birlesik_anahtar.json`, `B_anahtar.json`, `A_sistem_gizli.json`
- Araçlar: `testseti/araclar/k45_havuz.py`, `k45_ortak.py`, `k45_sistem.py`, `k45_hazirla.py`, `k45_a_birlestir.py`, `k45_kurul.py`, `k45_oyla.py`
