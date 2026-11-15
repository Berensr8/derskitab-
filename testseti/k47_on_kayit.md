# K47: Yeni Araçların Taraması — Ön Kayıt

- **Tarih:** 2026-11-15
- **Amaç:** K42 ve K45 bağımsız değerlendirmelerinde kaçan hata sınıflarını (noktalama, sözlükte geçerli veya tek kelimelik yazım hataları, bağlamsal kelime hataları) genel olarak yakalayabilecek üç aracı (`ytu-ce-cosmos/turkish-base-bert-punctuation-correction`, `hunspell-tr`, yerel dil modelleriyle temiz sayfa okuma: `qwen3.5:9b` ve `gemma4:12b-it-qat`) elimizdeki etiketli 60 sayfada ayar yapmadan taramak ve denemeye değenleri ayırmak.
- **Niteliği:** Bu çalışma bir **tarama**dır, ürün ölçümü değildir (60 sayfa daha önce K42 ve K45'te görülmüştür). Ürün koduna (`derskitabi/`) dokunulmaz.
- **Ölçülen mevcut ürün kodu (`HEAD`):** `ce96bf8` (K46 dahil: `ab3d3e8`).
- **Rastgele örneklem tohumu:** `20261117` (her araç için 10 rastgele eşleşmeyen işaret örneği seçimi).

---

## 1. Veri ve Hata Sınıfları (44 Gerçek Hata)

- **Sayfalar (60 sayfa):**
  - K42 A sayfaları (30 sayfa, `bagimsiz_degerlendirme2/A_sayfa_listesi.json`: `biyoloji9`, `biyoloji11`, `turkdili10`).
  - K45 A sayfaları (30 sayfa, `bagimsiz_degerlendirme3/A_sayfa_listesi.json`: `biyoloji12`, `inkilap12`).
- **Sayfa metni kaynağı:** Ürünün kendi blok dosyaları (`veri/<kitap>_bloklar.json`, yumuşak tire temizlenmiş). `A_30_sayfa_metin.txt` dosyaları kullanılmaz.
- **Doğru cevap zemini:** Bağımsız kurulun çoğunluk oyuyla (`HATA`) belirlediği A maddeleri: K42'de **17**, K45'te **27**, toplam **44 gerçek hata**. Kurulun `DEGIL` (veya `BELIRSIZ`) dediği A adayları (K42'de 65, K45'te 41; toplam **106 aday**) "kurulun reddettiği" olarak ayrıca sayılır.

### Mekanik Hata Sınıflama Kuralı
`kitaptaki` ($k$) ve `onerilen` ($o$) metinleri için:
1. **Noktalama sınıfı (13 hata):** Noktalama işaretleri (`, ; : ? ! .`) ve bunların etrafındaki boşluklar tek boşluğa indirgendiğinde (`re.sub(r"\s+", " ", re.sub(r"\s*[,;:?!.]+\s*", " ", s.strip())).strip()`) $k$ ve $o$ birebir aynı oluyorsa (`k != o`).
2. **Kelime sınıfı (9 hata):** Noktalama sınıfında değilse, hem $k$ hem $o$ tek kelimelikse (`len(k.split()) == 1 and len(o.split()) == 1`) ve ikisi de en az bir harf (`isalpha()`) içeriyorsa.
3. **Diğer sınıfı (22 hata):** Geri kalan çok kelimelik, kesme/boşluk dizgisi veya büyük/küçük harf hataları.

### 44 Gerçek Hatanın Sınıf Listesi

#### A. Noktalama Sınıfı (13 hata)
1. `K42_A05` (`K42_S03`, `biyoloji9` s. 87): `yazınız..` $\rightarrow$ `yazınız.`
2. `K42_A08` (`K42_S07`, `biyoloji9` s. 150): `Yönerge :` $\rightarrow$ `Yönerge:`
3. `K42_A09` (`K42_S08`, `biyoloji9` s. 155): `11,12, 13` $\rightarrow$ `11, 12, 13`
4. `K42_A14` (`K42_S18`, `biyoloji11` s. 158): `akıllı termostatlar;` $\rightarrow$ `akıllı termostatlar`
5. `K42_A15` (`K42_S18`, `biyoloji11` s. 158): `örnek veriniz?` $\rightarrow$ `örnek veriniz.`
6. `K42_A18` (`K42_S20`, `biyoloji11` s. 224): `solunum hızı;` $\rightarrow$ `solunum hızı,`
7. `K42_A79` (`K42_S30`, `turkdili10` s. 292): `1947,1962` $\rightarrow$ `1947, 1962`
8. `K45_A02` (`K45_S01`, `biyoloji12` s. 17): `(Görsel 1.2)],1869` $\rightarrow$ `(Görsel 1.2)], 1869`
9. `K45_A13` (`K45_S07`, `biyoloji12` s. 111): `gece gündüz fotosentezi` $\rightarrow$ `gece gündüz, fotosentezi`
10. `K45_A19` (`K45_S10`, `biyoloji12` s. 137): `Kloroplast içermez bu yüzden` $\rightarrow$ `Kloroplast içermez, bu yüzden`
11. `K45_A23` (`K45_S12`, `biyoloji12` s. 165): `Ksilemdeki su ,` $\rightarrow$ `Ksilemdeki su,`
12. `K45_A39` (`K45_S20`, `inkilap12` s. 130): `Kazım Karabekir;` $\rightarrow$ `Kazım Karabekir`
13. `K45_A46` (`K45_S20`, `inkilap12` s. 130): `riya tembellik` $\rightarrow$ `riya, tembellik`

#### B. Kelime Sınıfı (9 hata)
1. `K42_A04` (`K42_S02`, `biyoloji9` s. 76): `Commasie` $\rightarrow$ `Coomassie`
2. `K42_A07` (`K42_S06`, `biyoloji9` s. 142): `coğrafik` $\rightarrow$ `coğrafi`
3. `K42_A11` (`K42_S08`, `biyoloji9` s. 155): `Canidea` $\rightarrow$ `Canidae`
4. `K42_A23` (`K42_S21`, `turkdili10` s. 68): `gr` $\rightarrow$ `g`
5. `K42_A36` (`K42_S25`, `turkdili10` s. 106): `’abesdir` $\rightarrow$ `abestir`
6. `K45_A29` (`K45_S15`, `biyoloji12` s. 190): `işaretleyiz` $\rightarrow$ `işaretleyiniz`
7. `K45_A58` (`K45_S25`, `inkilap12` s. 179): `kollektifleştirme` $\rightarrow$ `kolektifleştirme`
8. `K45_A64` (`K45_S29`, `inkilap12` s. 262): `COVİD-19` $\rightarrow$ `COVID-19`
9. `K45_A66` (`K45_S30`, `inkilap12` s. 273): `Yarımada’yı` $\rightarrow$ `yarımadayı`

#### C. Diğer Sınıfı (22 hata)
1. `K42_A02` (`K42_S02`, `biyoloji9` s. 76): `Form11` $\rightarrow$ `Form 11`
2. `K42_A10` (`K42_S08`, `biyoloji9` s. 155): `Canis familaris` $\rightarrow$ `Canis familiaris`
3. `K42_A17` (`K42_S19`, `biyoloji11` s. 167): `Kap atışı` $\rightarrow$ `Kalp atışı`
4. `K42_A29` (`K42_S24`, `turkdili10` s. 84): `bir takım vasıflar` $\rightarrow$ `birtakım vasıflar`
5. `K42_A50` (`K42_S27`, `turkdili10` s. 237): `Sözlü alarak ifade ediniz.` $\rightarrow$ `Sözlü olarak ifade ediniz.`
6. `K45_A01` (`K45_S01`, `biyoloji12` s. 17): `1953’ te` $\rightarrow$ `1953’te`
7. `K45_A04` (`K45_S02`, `biyoloji12` s. 19): `Görsel 1.8’ de` $\rightarrow$ `Görsel 1.8’de`
8. `K45_A05` (`K45_S03`, `biyoloji12` s. 71): `Görsel 2.2 ‘de` $\rightarrow$ `Görsel 2.2’de`
9. `K45_A06` (`K45_S03`, `biyoloji12` s. 71): `tepkimelerine endergonik tepkimeler, enerji açığa çıkaran tepkimelerine ise` $\rightarrow$ `tepkimelere endergonik tepkimeler, enerji açığa çıkaran tepkimelere ise`
10. `K45_A08` (`K45_S04`, `biyoloji12` s. 77): `Engelman deneyi` $\rightarrow$ `Engelmann deneyi`
11. `K45_A14` (`K45_S07`, `biyoloji12` s. 111): `H2S’ dir` $\rightarrow$ `H2S’dir`
12. `K45_A15` (`K45_S07`, `biyoloji12` s. 111): `O2 dir` $\rightarrow$ `O2’dir`
13. `K45_A17` (`K45_S07`, `biyoloji12` s. 111): `Farklı yönleri` $\rightarrow$ `Farklı Yönleri`
14. `K45_A20` (`K45_S10`, `biyoloji12` s. 137): `Yaprağının enine kesitinde` $\rightarrow$ `Yaprağın enine kesitinde`
15. `K45_A22` (`K45_S11`, `biyoloji12` s. 164): `%78’ i` $\rightarrow$ `%78’i`
16. `K45_A24` (`K45_S12`, `biyoloji12` s. 165): `Ksilem de` $\rightarrow$ `Ksilemde`
17. `K45_A28` (`K45_S14`, `biyoloji12` s. 186): `Oksin hormonun` $\rightarrow$ `Oksin hormonunun`
18. `K45_A51` (`K45_S21`, `inkilap12` s. 141): `Türkiye Cumhuriyetine` $\rightarrow$ `Türkiye Cumhuriyeti’ne`
19. `K45_A52` (`K45_S22`, `inkilap12` s. 150): `ve tabi bu arada` $\rightarrow$ `ve tabii bu arada`
20. `K45_A53` (`K45_S22`, `inkilap12` s. 150): `Büyük Millet Meclis` $\rightarrow$ `Büyük Millet Meclisi`
21. `K45_A60` (`K45_S27`, `inkilap12` s. 205): `Demokrat Parti (DP)’nin` $\rightarrow$ `Demokrat Partinin (DP)`
22. `K45_A63` (`K45_S29`, `inkilap12` s. 262): `suv modeli` $\rightarrow$ `SUV modeli`

---

## 2. Eşleşme Kuralı (K43 ile Aynı, Mekanik)

- **Normalleştirme (`norm`):** Metin Türkçe küçük harfe (`tr_kucuk`) çevrilir, kıvrık kesme/tırnak işaretleri (`’ ‘ “ ”`) düzleştirilir (`' "`) ve tüm boşluklar silinir (`re.sub(r"\s+", "", ...)`).
- **Eşleşme (`eslesir_mi`):** Aracın işaret ettiği `parca` (`len(norm(parca)) >= 2`), aynı sayfadaki bir gerçek hatanın (veya kurulun `DEGIL` dediği adayın) `kitaptaki` metnini içeriyorsa ya da `kitaptaki` metin `parca`'yı içeriyorsa eşleşmiş sayılır.
  - Noktalama modelinde (`Araç 1`), model bir kelimeden sonra eksik veya fazla noktalama işaretlediğinde aracın işaret ettiği parça o kelime ve hemen sağındaki kelimeyi kapsayan iki kelimelik metin parçası (`"<kelime_i>[varsa_isaret] <kelime_{i+1}>"`) olarak alınır; böylece hem `"Karabekir;"` gibi tek kelimeli noktalama hedefleriyle hem `"riya tembellik"` / `"içermez bu yüzden"` gibi iki kelimeli noktalama hedefleriyle mekanik olarak karşılaştırılır.

---

## 3. Araç Yöntemleri, Eşikler ve Geçme Ölçütleri

### Araç 1: Noktalama Modeli (`ytu-ce-cosmos/turkish-base-bert-punctuation-correction`)
- **Model yolu:** `modeller/ytu-ce-cosmos__turkish-base-bert-punctuation-correction/`
- **Kapsam:** 60 sayfadaki `tur == "paragraf"` blokları; ürünün `derskitabi.kriterler.alinti.alinti_ve_replik_bloklari(bloklar)` fonksiyonunun alıntı veya replik dediği bloklar atlanır.
- **Yöntem:**
  - Bloklar `derskitabi.kriterler.okunabilirlik.cumlelere_bol` ile cümlelere ayrılır.
  - Her cümlede kelimeler ve kelimelerden hemen sonra gelen gerçek noktalama işaretleri (`, ; : ? ! .`) çıkarılır; model README'sindeki `preprocess` fonksiyonuyla (`'` ve `-` boşluğa çevrilip `I -> ı` ve `.lower()` uygulanarak) alt parçalara (subword) bölünür.
  - Her kelimenin **son alt parçasındaki** (`##` ile devam etmeyen son token) softmax olasılık dağılımı okunur; **cümle sonu (son kelime) değerlendirilmez**:
    - **Eksik noktalama:** Model `,` `;` `:` `?` etiketlerinden birini olasılık **$\ge 0,95$** ile tahmin ediyor ve kitapta o kelimeden sonra herhangi bir noktalama işareti yok.
    - **Fazla noktalama:** Kitapta kelimeden sonra `,` ya da `;` var ve model `non` etiketini olasılık **$\ge 0,95$** ile tahmin ediyor.
  - Bilgi için `0,90` ve `0,99` eşiklerindeki sayılar da raporlanır; **karar `0,95` eşiğine göre verilir.**
- **Geçme ölçütü:** Noktalama sınıfındaki 13 gerçek hatanın **en az yarısı ($\ge 7/13$)** bulunur **ve** gerçek hatayla eşleşmeyen işaret sayısı sayfa başına **1'den az ($< 1,0$ / sayfa, yani 60 sayfada $< 60$)** olur.

### Araç 2: `hunspell-tr` (`modeller/hunspell-tr/tr_TR` + `spylls`)
- **(a) Yanlış alarm süzgeci:**
  - Veri: K42 (`veri/bagimsiz2/B_anahtar.json`, 25 hakemli / 38 birleşik) ve K45 (`veri/bagimsiz3/B_anahtar.json`, 76 hakemli / 129 birleşik katman-temiz) B listelerindeki kurul etiketli `morfoloji` tespitleri (hem hakemli gösterilen kümede hem birleşik B kümesinde ayrı ayrı raporlanır; karar hakemli gösterilen kümede değerlendirilir).
  - Kural: `spylls` (`Dictionary.from_files`) kelimeyi (veya Türkçe küçük harfli biçimini) `lookup()` ile geçerli sayarsa tespit düşük önceliğe inerdi.
  - **Geçme ölçütü:** **En çok 1 `HATA` kaybı ($\le 1$)** **ve** `DEGIL` olanların **en az %30'u ($\ge %30$)** iner.
- **(b) Bulucu:**
  - Veri: 60 A sayfasındaki bloklarda (` yazim.py` ile aynı kelime ayıklama ve alıntı/terim/PDF düşük öncelik süzgecinden sonra) Starlang ve Zemberek'in geçerli saydığı (mevcut sistemin morfoloji hatası olarak göstermediği) ama `hunspell.lookup` fonksiyonunun (hem özgün hem küçük harfli biçimiyle) tanımadığı kelimeler.
  - **Geçme ölçütü:** Kelime sınıfındaki 9 gerçek hatadan **en az 3'ünü ($\ge 3/9$)** yakalar **ve** sayfa başına **1'den az ($< 1,0$ / sayfa, yani 60 sayfada $< 60$)** eşleşmeyen işaret üretir.
- **Bilgi için (öneri kalitesi):** `hunspell.suggest()` çıktısının ilk 3 önerisi, kelime sınıfındaki gerçek hataların ve B listesindeki gerçek `morfoloji` hatalarının doğrusunu içeriyor mu?

### Araç 3: Yerel Modelle Sayfa Okuma (Temiz Metinle — `qwen3.5:9b` ve `gemma4:12b-it-qat`)
- **Modeller:** Sırayla `qwen3.5:9b` ve `gemma4:12b-it-qat` (`temperature=0`, `num_ctx=4096`, `num_predict=1024`).
- **İstem ve şema:** K43 ön kaydındaki (`testseti/k43_on_kayit.md`) `SISTEM`, `SORU_SABLONU` ve `OZELLIKLER` JSON şeması **birebir aynı** kullanılır:
  - `SISTEM`: `"Sen Türkçe ders kitapları için çalışan bir yazım editörüsün. Bu ders kitabı sayfasında yazım, noktalama, dizgi ve yanlış kullanılmış kelime hatalarını bul. Eski metin alıntılarını, şiirleri ve ağız özelliklerini hata sayma. Her hata için kitaptaki hâlini, önerini ve kısa gerekçeni ver. Emin değilsen yazma. Sayfada hata yoksa boş liste döndür."`
- **Sayfa metni:** O sayfanın `veri/<kitap>_bloklar.json` içindeki bloklarının metni, okuma sırasıyla (`\n\n` ile birleştirilmiş, alıntı/replik blokları dahil; 4000 karakteri aşarsa K43'teki gibi paragraf sınırından bölünerek).
- **Geçme ölçütü (model başına):**
  1. 44 gerçek hatanın **en az 15'ini ($\ge 15/44$)** bulur,
  2. Sayfa başına ortalama **3'ten az ($< 3,0$ aday/sayfa, yani 60 sayfada $< 180$ toplam aday)** üretir,
  3. Mevcut sistemin (`HEAD`, güven $\ge 0,5$) bulmadığı **en az 8 gerçek hatayı ($\ge 8$)** yakalar.
- Sayfa başına süre ve 300 sayfalık kitap için süre tahmini ayrıca raporlanır.
