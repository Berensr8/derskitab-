# Okunabilirlik kriteri — değerlendirme (K24)

- **Tarih:** 2026-10-20 · **Kod sürümü:** `db7bcef` + bu değerlendirme betiği (`derskitabi/degerlendirme_okunabilirlik.py`); okunabilirlik kriterinde hiçbir ayar yapılmadı.
- **Doğru cevap yok:** Paragrafların sınıf düzeyi elle etiketlenmedi; bilinen tek nesnel bilgi paragrafın hangi sınıfın kitabından geldiği. Ölçümler buna dayanıyor.
- **Eklenen paragraflar:** `okunabilirlik_eklemeleri.json` (sabit tohum 20261020; SHA-256 `38a141fb…`): Biyoloji 10'dan 30, TDE 9'dan 30 rastgele paragraf (≥3 cümle).

## 1. Kitap düzeyi (ortanca puanlar)

| Sınıf | Kitap | Ateşman (yüksek = kolay) | Çetinkaya-Uzun (yüksek = kolay) | Bezirci-Yılmaz (yüksek = zor) |
|---|---|---|---|---|
| 6 | Sosyal Bilgiler | 67,9 | 40,0 | 6,3 (ilköğretim) |
| 9 | Türk Dili ve Edebiyatı | 62,4 | 37,0 | 7,9 (ilköğretim) |
| 10 | Biyoloji | 46,6 | 28,5 | 13,0 (lisans) |
| 11 | Matematik | 69,3 | 41,9 | 8,1 (lise) |

Puanlar sınıf sırasını izlemiyor: 11. sınıf Matematik formüllere göre en kolay kitap.

## 2. Ayırt etme gücü (AUC, 6. sınıf kitabına karşı)

Üst sınıf kitabından rastgele bir paragrafın, 6. sınıf kitabından rastgele bir paragraftan "daha zor" çıkma olasılığı (0,5 = yazı tura).

| Kitap | Ateşman | Çetinkaya-Uzun | Bezirci-Yılmaz |
|---|---|---|---|
| TDE 9 | 0,39 | 0,39 | 0,39 |
| Biyoloji 10 | 0,65 | 0,65 | 0,67 |
| Matematik 11 | 0,51 | 0,50 | 0,52 |

## 3. Ekleme testi

6. sınıf kitabına 60 üst sınıf paragrafı eklendi; sistem kendi yöntemiyle (kitabın en zor %10'u, en az 2 formül hemfikir) işaretledi.

| Paragraflar | İşaretlenme oranı |
|---|---|
| Kitabın kendi paragrafları (375) | %8,8 |
| Biyoloji 10'dan eklenen (30) | %13,3 |
| TDE 9'dan eklenen (30) | %10,0 |

## Yorum

- Klasik okunabilirlik formülleri yalnız **cümle ve kelime uzunluğunu** ölçer; kavramsal zorluğu (terimler, soyutluk, ön bilgi) ölçmez. Matematik metinleri kısa cümleli olduğu için kolay, edebiyat kitabındaki şiir ve diyaloglar da kısa olduğu için kolay görünüyor. Bu, literatürdeki bilinen eleştiriyle uyumlu.
- Bu yüzden sistemin okunabilirlik çıktısı **"sınıfa uygunluk" değil, "dilsel karmaşıklık uyarısı"** olarak sunulmalı: kitabın kendi içinde belirgin şekilde uzun cümleli / uzun kelimeli paragrafları gösteriyor (sistem zaten "tek başına sınıfa uygun değil demek değildir" notunu gösteriyor).
- **Sınırlama:** Farklı derslerin kitapları karşılaştırıldı; ders farkı (edebiyat, matematik, fen) sınıf farkıyla karışıyor. Daha adil test: aynı dersin farklı sınıf kitapları (ör. Sosyal Bilgiler 5–7, Türkçe 5–8).
- **İyileştirme fikirleri (Faz 2):** terim yoğunluğu (morfolojinin tanımadığı / kitapta tekrar eden terimler), kelime sıklığı listeleri, sınıf ve ders başına MEB kitaplarından hesaplanan norm puanları, dil modeliyle sınıf düzeyi tahmini.

## 4. Ders içi karşılaştırma (2026-10-20 eki)

Ders farkının sınıf farkına karışmaması için aynı dersin farklı sınıf kitapları MEB OGM Materyal'den indirildi (Biyoloji 9 ve 11, TDE 10 ve 11). Ortancalar ≥3 cümleli paragraflar üzerinden.

| Ders | Sınıf | Paragraf | Ateşman | Çetinkaya-Uzun | Bezirci-Yılmaz |
|---|---|---|---|---|---|
| Biyoloji | 9 | 389 | 45,2 | 28,7 | 16,7 |
| Biyoloji | 10 | 382 | 45,7 | 29,2 | 16,9 |
| Biyoloji | 11 | 442 | 52,0 | 32,3 | 14,3 |
| TDE | 9 | 678 | 63,8 | 38,8 | 9,5 |
| TDE | 10 | 470 | 74,5 | 44,4 | 6,3 |
| TDE | 11 | 506 | 70,5 | 41,6 | 7,4 |

| Karşılaştırma (üst sınıf "daha zor" olasılığı) | Ateşman | Çetinkaya-Uzun | Bezirci-Yılmaz |
|---|---|---|---|
| Biyoloji 10 > 9 | 0,49 | 0,48 | 0,52 |
| Biyoloji 11 > 9 | 0,39 | 0,38 | 0,40 |
| Biyoloji 11 > 10 | 0,40 | 0,40 | 0,38 |
| TDE 10 > 9 | 0,41 | 0,42 | 0,41 |
| TDE 11 > 9 | 0,45 | 0,45 | 0,45 |
| TDE 11 > 10 | 0,54 | 0,54 | 0,55 |

**Yorum:** Aynı ders içinde de formüller sınıf düzeyini ayırt etmiyor. Aynı öğretim programına ait kitaplar arasında (Biyoloji 9–10, ikisi de yeni programın "Tema" düzeninde; TDE 10–11, ikisi de "Ünite" düzeninde) fark yazı tura düzeyinde (AUC 0,49–0,55). Üst sınıfların "daha kolay" çıktığı karşılaştırmalar (Biyoloji 11, TDE 10) eski program ile yeni program arasında — yani formüllerin yakaladığı şey sınıf düzeyi değil, kitabın yazım üslubu (cümle ve kelime uzunluğu). K24 bulgusu güçlendi: çıktı "dilsel karmaşıklık uyarısı" olarak sunulmalı; sınıf düzeyi için kavramsal zorluğu (terimler, ön bilgi) ölçen yöntemler gerekir.
