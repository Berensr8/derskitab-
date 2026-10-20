# Tutarlılık kriteri — kilitli test seti sonuçları (K20)

- **Tarih:** 2026-10-20 · **Kod sürümü:** `d36da3f` (ayarlar `118288a`'da donduruldu; arada yalnız hata yönetimi değişti)
- **Set:** `tutarlilik_celiskileri.json` (SHA-256 `740101f4…`), 35 test maddesi (Sosyal Bilgiler 6: 18, Biyoloji 10: 17). Test maddeleri yalnız bu koşuda kullanıldı.
- **Modeller:** bge-m3 (aday bulma), gemma4:12b-it-qat (hakem), Turkish-Gemma-9b-T1 (ikinci görüş) — yerel, Ollama.

## Ana sonuç

| Ölçüt | Değer |
|---|---|
| Recall (eklenen çelişkilerin bulunma oranı) | **27/35 = %77,1** |
| Recall, geçersiz madde (B17) hariç | **27/34 = %79,4** |
| Recall, yalnız yüksek güven (1,0) | 24/35 = %68,6 |
| Precision (tespitlerin doğru olanı) | **27/27 = %100** (eklenmemiş tespit: 0) |

Kitapların kendisinde (çelişki eklenmeden) yapılan tam çalıştırmalarda gerçek bir çelişki bulunmadı; son ayarlarla sahte tespit de çıkmadı.

## Aşama aşama (35 madde)

| Aşama | Ulaşan |
|---|---|
| Cümle bilgi cümlesi olarak seçildi | 34 |
| Kaynakla aday çift oldu (bge-m3) | 32 |
| Hızlı tur "çelişki" dedi (gemma4) | 31 |
| Son tespit | 27 |

## Türe, konuma ve yönteme göre recall

| Tür | Recall | | Konum | Recall | | Yöntem | Recall |
|---|---|---|---|---|---|---|---|
| tarih | 1,00 | | düz metin | 0,77 | | tekrar bozma | 0,83 |
| isim | 1,00 | | etkinlik metni | 0,80 | | yeniden yazma | 0,74 |
| sayı | 0,82 | | | | | | |
| sözel | 0,67 | | | | | | |
| en/ilk | 0,57 | | | | | | |

## Kaçanlar

- **Aday bulunamadı (2):** B16 ("CO₂ günümüzde 300 ppm'nin altında" ↔ "421 ppm"), S22 ("en kalabalık ikinci il İzmir" ↔ sayılarla verilen il sıralaması) — anlamca farklı ifade edilmiş.
- **Hakemler çelişki görmedi (5):** B07, B20, B22, S08, S23 — çoğu "en/ilk" ve sözel (ör. kuşlarda mide bölümlerinin sırası, "ilk" koruma enstitüsü).
- **Geçersiz madde (1):** B17 — kaynak cümle bir karakter konuşmasında ("Ali: …"); setin kendi tanımına göre kitabın iddiası değil, sistem doğru davranıp dışarıda bıraktı. Set hazırlanırken gözden kaçtı.

## Puanlama hakkında not

İlk betik çıktısı recall 0,743 / precision 0,897 idi. Fark tek bir maddeden (S09) geliyor: sistem "Hicret 632" çelişkisini kitaptaki iki ayrı "622" cümlesiyle buldu (güven 1,0), ama cümle bölücü "Hz." kısaltmasında cümleyi böldüğü için puanlama betiği eklenen cümleyi tanıyamadı ve bu tespitleri "fazladan" saydı. Puanlama betiği bölünmüş cümleleri de tanıyacak şekilde düzeltildi; sistemin kararları önbellekten aynen yeniden sayıldı (hiçbir model yeniden çalıştırılmadı).

## Sınırlamalar

- Çelişkileri sistemi geliştiren taraf (Claude) yazdı; set gözden geçirmesini de kullanıcının isteğiyle Claude yaptı.
- 35 madde küçük bir örneklem: tek bir madde recall'ı ~3 puan oynatır.
- Gerçek kitap hataları farklı dağılabilir (ör. daha uzak sayfalarda, daha farklı ifadelerle).
