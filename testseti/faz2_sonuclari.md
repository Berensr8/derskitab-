# Faz 2 — kapanış sonuçları (2026-10-21)

Faz 2'de eklenenler: notlu PDF (K26), Excel inceleme raporu (K27), alıntı ayırma (K28, v3 K29), PDF okuma
parçası ve terim tanıma (K29), tutarlılıkta alıntı/replik süzgeci (K29), yazım hakeminde hece koruması
(K25 eki), kavramsal okunabilirlik denemesi (K30, olumsuz). Betik: `testseti/araclar/faz2_kapanis.py`
(kod `4380aec`); yazım hakemi cevapları önbellekten.

## 1. Yazım: gösterilen tespitler, Faz 1 → Faz 2 (9 kitap)

Hiçbir tespit silinmez; "düşük öncelik" tespitleri notlu PDF'e eklenmez (isteğe bağlı), Excel raporunda
sebebiyle durur.

| Kitap | Tespit | Faz 1 gösterilen | Faz 2 gösterilen | PDF parçası | Terim | Alıntı | Hakem "muhtemelen doğru" |
|---|---|---|---|---|---|---|---|
| Sosyal Bilgiler 6 | 77 | 77 | 38 | 0 | 3 | 2 | 34 |
| Biyoloji 9 | 253 | 253 | 46 | 3 | 13 | 0 | 191 |
| Biyoloji 10 | 177 | 177 | 21 | 15 | 13 | 0 | 128 |
| Biyoloji 11 | 275 | 275 | 51 | 3 | 22 | 4 | 195 |
| Matematik 11 | 77 | 77 | 42 | 10 | 0 | 0 | 25 |
| TDE 9 | 433 | 433 | 93 | 3 | 0 | 203 | 134 |
| TDE 10 | 572 | 572 | 76 | 5 | 3 | 354 | 134 |
| TDE 11 | 476 | 476 | 105 | 7 | 42 | 232 | 90 |
| TDE 12 | 403 | 403 | 156 | 25 | 6 | 82 | 134 |
| **Toplam** | **2.743** | **2.743** | **628 (%23)** | 71 | 102 | 877 | 1.065 |

## 2. Yazım: etiketli örneklemlerde isabet

Gösterilen tespitlerden gerçek hata olanlar ("belirsiz" etiketler paydada yok). K23/K25 etiketleri ve
K29 testi Faz 2 geliştirmesinde görüldü; bu tablo özettir, temiz test değildir (temiz ölçümler: K28 TDE 11,
K29 körlemesine test — `KARARLAR.md`).

| Örneklem | Faz 1 | Faz 2 | Düşük önceliğe inen gerçek hata |
|---|---|---|---|
| K23 Sosyal Bilgiler 6 (hepsi) | 20/66 (%30) | 20/29 (%69) | 0 |
| K23 Biyoloji 10 (50) | 3/50 (%6) | 3/9 (%33) | 0 |
| K25 Matematik 11 (40) | 8/35 (%23) | 8/23 (%35) | 0 |
| K25 TDE 9 (40) | 0/39 | 0/6 | — |
| K29 Biyoloji 9 (50) | 0/50 | 0/5 | — |
| K29 Biyoloji 11 (50) | 5/49 (%10) | 5/7 (%71) | 0 |
| K29 TDE 12 (80) | 1/79 (%1) | 1/27 (%4) | 0 |
| **Toplam** | 37 gerçek / 368 gösterilen | 37 gerçek / 106 gösterilen | **0 / 37** |

Gösterilen sahte tespit 331 → 69. Recall (kilitli 56 eklenmiş hata, K23): hakemsiz 56/56, hakemle 55/56
(kaçan "kaldirmıştır": model Türkçe harf hatasının üzerinden okuyor — K25'ten bilinen).

## 3. Bilgi tutarsızlığı

| Kitap | Tespit | Not |
|---|---|---|
| Sosyal Bilgiler 6 | 0 | |
| Biyoloji 10 | 0 | |
| TDE 11 | 0 | önce 1 sahte (Cimri replikleri) — alıntılar artık karşılaştırılmıyor |
| TDE 12 | 1 (sahte, 0,5) | iki farklı şairin biyografisi; satır blokları cümlenin öznesini koparıyor |

Geliştirme seti (K20): recall 13/15, precision 13/13 (değişmedi). Kilitli test (Faz 1): 27/35, 27/27.

## 4. Okunabilirlik / kavramsal yük (K30)

Önceden sabit ölçüt (aynı programın kitapları arasında AUC ≥ 0,60, bütün çiftlerde ≥ 0,55) hiçbir yöntemde
tutmadı: formüller (K24), nadir kelime oranı, ortalama sıklık sırası, terim oranı, dil modeliyle sınıf tahmini
(model neredeyse her kitaba "9. sınıf" diyor). Çıktı "dilsel karmaşıklık uyarısı" olarak kalır; sınıf
düzeyi için öğretmen etiketi gerekir (gelecek çalışma).

## 5. Bilinen sınırlamalar

- Edebiyat kitaplarında yazım isabeti hâlâ düşük: alıntı ayırma dizgiye bağlı (TDE 12'nin dizgisinde
  alıntıların çoğu kaçıyor); kalan sahtelerin çoğu alıntıdaki eski yazım.
- Yazım hakemi küçük hataların "üzerinden okuyabiliyor" (kaldirmıştır); korumalar tek harf ve tekrarlanan hece.
- PDF'te dar kutulardaki (biyografi, kenar notu) her satır ayrı blok: cümleler bölünüyor.
- Sosyal 6'da birkaç yanlış alıntı bloğu (görsel etiketleri), tespit etkilenmiyor.
- Tutarlılıkta "en/ilk" ve sözel çelişkiler zayıf (K20 testi); daha büyük model gerekir.
