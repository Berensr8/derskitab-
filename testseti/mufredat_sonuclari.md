# Müfredat uyumu (Faz 3, K31) — sonuçlar (2026-10-27)

Soru: kitap, MEB öğretim programının (Türkiye Yüzyılı Maarif Modeli, tymm.meb.gov.tr) öğrenme çıktılarını
karşılıyor mu? İki yöntem denendi:

1. **Çıktı kapsamı (dil modeli):** öğrenme çıktısı + içerik çerçevesi bge-m3 ile kitabın paragraflarına
   benzetilir, en yakın 5 paragraf gemma4'e sorulur: karşılanıyor / kısmen / karşılanmıyor.
2. **Anahtar kavram kontrolü (kural tabanlı):** programın her çıktı grubu için verdiği anahtar kavramlar
   kitabın konu anlatımında geçiyor mu.

Ölçüt ve karar kuralı ölçümden önce `KARARLAR.md` K31'e yazıldı; betik `derskitabi/degerlendirme_mufredat.py`,
sonuçlar `veri/degerlendirme_mufredat*.json` (git dışında).

**Karar: çıktı kapsamı ölçütü geçmedi → ürüne yalnız anahtar kavram kontrolü girdi.**

## 1. Çıktı kapsamı

Pozitif = kitabın kendi sınıfının (ve kapsadığı temaların) çıktıları, "karşılanıyor/kısmen" beklenir.
Negatif = aynı dersin başka sınıflarının çıktıları (ve Sosyal 6'da kitapta olmayan öğrenme alanları),
"karşılanıyor" demesi yanlış. Konum = karşılanan çıktıda en benzer paragrafın sayfası çıktının temasında mı.

| Ölçüm | Kitap | Pozitif kapsam (≥ 0,85) | Negatifte "karşılanıyor" (≤ 0,30) | Konum (hedef ≥ 0,75) |
|---|---|---|---|---|
| İlk (d69eac0) | Biyoloji 9 | 13/14 = 0,93 | 14/61 = 0,23 | 10/13 |
| | Biyoloji 10 | 17/19 = 0,89 | 3/56 = 0,05 | **1/17** |
| | Sosyal Bilgiler 6 | 10/10 = 1,00 | 13/60 = 0,22 | 6/10 |
| Düzeltme sonrası (3369c62), temiz değil | Biyoloji 9 | 10/14 = 0,71 | 16/61 = 0,26 | 8/10 |
| | Biyoloji 10 | 15/19 = 0,79 | 3/56 = 0,05 | 15/15 |
| | Sosyal Bilgiler 6 | 10/10 = 1,00 | 13/60 = 0,22 | 10/10 |
| **Temiz doğrulama** | **Biyoloji 11** | **18/22 = 0,82 ✗** | **7/53 = 0,13 ✓** | **18/18** |

**Eksik tema testi** (bir temanın sayfaları kitaptan çıkarılır; o temanın çıktılarının ≥ %80'i
"karşılanmıyor"a dönmeli, kalan temanınkiler ≥ %80 karşılanıyor kalmalı):

| Ölçüm | Kitap, çıkarılan | Çıkarılan tema "karşılanmıyor" | Kalan tema karşılanıyor/kısmen |
|---|---|---|---|
| İlk | Biyoloji 9, Tema 2 | 3/6 ✗ | 7/8 |
| Düzeltme sonrası | Biyoloji 9, Tema 2 | 4/6 ✗ | 4/8 ✗ |
| **Temiz doğrulama** | **Biyoloji 11, Tema 2** | **5/10 ✗** | **9/12 ✗** |

**Düzeltme (K31 eki):** ilk ölçümde en benzer paragraf çoğunlukla tema / öğrenme alanı **kapak sayfasıydı**;
kapak programın içerik çerçevesini aynen aktarıyor (Biyoloji 10 s.15 bütün Tema 1 çıktılarının ilk adayı).
Kapak, içindekiler, tema sunusu, kitabı tanıtım sayfaları aday paragraflardan ve kavram kontrolünden çıkarıldı;
değerlendirmede kapak açtığı temaya bağlandı (kapağın sayfa başlığı yok, önceki temaya sayılıyordu).
Düzeltme sonuçlara bakılarak yapıldığı için karar, hiç çalıştırılmamış Biyoloji 11 ile verildi.

**Yorum:**
- Konum güvenilir: model bir çıktıyı "karşılanıyor" dediğinde gösterilen sayfa doğru temada (temiz: 18/18).
- Karar güvenilir değil, iki yönde:
  - Kitapta işlenen konuları kaçırıyor. Örnekler: Biyoloji 11'de kas kasılma mekanizması, bağışıklığın
    sınıflandırılması ve alerji. Model, getirilen 5 paragrafta konunun ayrıntısını bulamıyor; doğru
    paragraf en yakın 5'in arasına girmiyor.
  - Çıkarılan bir temayı "var" sayıyor. Örnek: Biyoloji 11 Tema 2 (Homeostazi) çıkarılınca, Tema 1'deki
    hormon ve boşaltım paragrafları homeostazi çıktılarına "karşılanıyor" dedirtiyor. Bunun bir kısmı
    gerçek konu örtüşmesi.
- Sonuç: kesin bir "bu çıktı kitapta yok" kararı verdirmek için daha iyi bir arama gerekir (bölüm bölüm
  bakmak, daha çok aday). Bu Faz 3'te açık kalan bir iş. Yöntem `--kapsam` ile deneysel olarak duruyor.

## 2. Anahtar kavram kontrolü (ürüne giren)

Kavram, kitabın konu anlatımında (kapak, içindekiler ve tema sunusu dışında) ekli biçimiyle aranır
("ökaryot" → "ökaryotlar"). Çok kelimeli kavramda bütün kelimeler aynı sayfada geçerse "geçiyor" sayılır
("kan basıncı dengesi" ↔ "kan basıncını düzenleyen… dengesi"). Parantez içi ayrıca aranır ("STK").
Bir temanın kavramlarının en az yarısı yoksa tek not verilir: tema kitapta işlenmemiş ya da başka bir ciltte.

| Kitap (program ve sınıf otomatik) | Kendi kavramları kitapta | Bildirilen |
|---|---|---|
| Biyoloji 9 | 30/31 | "polimerizasyon" yalnız tanıtım/kapak sayfasında geçiyor (s. 12, 15); konu anlatımında "polimer" var, terim yok |
| Biyoloji 10 | 20/20 | — |
| Biyoloji 11 | 16/16 | — |
| Sosyal Bilgiler 6 ("1. Kitap": 1–3. alanlar) | 30/30 (1–3. alanlar) | 4. ve 6. öğrenme alanı "kitapta yok" (doğru: ikinci ciltte); 5. alandan 3 kavram (pazarlama, yatırım, üretim-dağıtım-tüketim) |
| TDE 9–12, Matematik 11 | — | program eşleşmedi (doğru: TDE programı beceri temelli, Matematik programı indirilmedi) |

Program eşleştirme: sınıf kapaktan okunur; o sınıfın kavramlarının en az yarısı kitapta geçen program seçilir
(Biyoloji ve Sosyal kitapları kendi programlarıyla 0,75–1,0; TDE ve Matematik kitapları Biyoloji programıyla
0,05–0,38).

**Sınırı (ölçüldü):** kontrol yalnız kitapta **hiç** geçmeyen kavramı yakalar. Bir tema çıkarıldığında
kavramlarının çoğu yine bulunur, çünkü başka temalarda da geçiyor ("hücre", "enerji"). Tema 2 çıkarılınca o
temaya özgü kavramlardan eksik bulunan: Biyoloji 9'da 5/17, Biyoloji 10'da 2/8, Biyoloji 11'de 2/7, Sosyal 6'da
1/9. Yani bir konunun eksik işlendiğini değil, programın bir terimini kitabın hiç kullanmadığını gösterir.
Kitabın ikinci cildinde olan alanlar gibi bütün bir temanın yokluğu ise yakalanıyor.

## 3. Üründe

- `python -m derskitabi.kriterler.mufredat <pdf>`: program ve sınıf otomatik; `--temalar 1-3` kitabın kapsadığı
  temaları sınırlar; `--kapsam` deneysel dil modeli kapsamı.
- Demo 5. adım; notlu PDF'te yeşil not (kavramın tanıtım sayfasında geçtiği sayfada ya da 1. sayfada) ve
  "Müfredat" yer imi bölümü; Excel raporunda "Müfredat" satırları ve özet sayfasında ölçülmüş başarı.
- İnceleme sayfasında (HTML) henüz yok.
