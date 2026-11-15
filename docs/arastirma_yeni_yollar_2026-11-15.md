# Yeni yollar araştırması: yazım ve noktalamada bulma oranını artırmak (2026-11-15)

## Neden

Üç bağımsız ölçüm (K39, K42, K45) aynı şeyi gösterdi: sistemin işaretledikleri yaklaşık dörtte bir isabetli,
hakem gizlemede çok iyi (48 tespitin 47'si doğru gizlendi), ama doğal kitap hatalarını bulma oranı çok düşük
(K42: 0/17, K45: 1/27). K44'te eklenen dokuz kural, hedeflediği kitapta 9/17 buldu ama yeni kitaplarda neredeyse
hiç çalışmadı: hata türleri kitaptan kitaba değişiyor. Bu yüzden tek tek kural yazmak yerine, kaçan hata
**sınıflarını** genel olarak ele alan araçlar arandı.

## Kaçan hataların sınıfları (K42 + K45, 44 gerçek hata)

| Sınıf | Örnek | Yaklaşık sayı |
|---|---|---|
| Noktalama (virgül eksik/fazla, noktalı virgül, soru işareti) | "içermez bu yüzden", "riya tembellik", "Karabekir;" | ~12 |
| Kesme ve boşluk dizgisi | "1953’ te", "Görsel 2.2 ‘de", "Form11", "Yönerge :" | ~10 (K46 kuralı ve K44 kuralları kısmen kapsıyor) |
| Kendi başına geçerli ama yanlış kelime | "Sözlü alarak", "Kap atışı", "Yaprağının", "hormonun", "Meclis" | ~10 |
| Yabancı ad ve terim | "Commasie", "Canis familaris", "Engelman", "COVİD-19" | ~6 |
| Büyük/küçük harf | "Farklı yönleri" (başlık), "suv" | ~3 |

## Bulunan araçlar

| Araç | Ne yapar | Hangi sınıfa | Boyut, lisans | Durum |
|---|---|---|---|---|
| ytu-ce-cosmos/turkish-base-bert-punctuation-correction | 8 noktalama işaretini tahmin eden ve düzelten BERT modeli (YTÜ COSMOS, 2024 makalesi) | Noktalama | 440 MB, MIT | İndirme gerekir |
| uygarkurt/bert-restore-punctuation-turkish | Nokta, virgül, soru işareti tahmini | Noktalama | 440 MB, MIT | Yedek seçenek (yalnız 3 işaret) |
| tdd-ai/hunspell-tr + spylls | Türkçe Hunspell sözlüğü (Deniz Yuret vd.), saf Python okuyucu | Yazım (üçüncü sözlük oyu) | 38 MB + 1,5 MB, MIT | İndirme gerekir |
| qwen3.5:9b (Ollama) | Daha yeni yerel dil modeli; K43'teki sayfa okumayı temiz metinle tekrar | Geçerli ama yanlış kelime, noktalama | Kurulu | İndirme gerekmez |
| VNLP (vngrs-nlp) | Bağlamlı yazım düzeltme (Jamspell) | Geçerli ama yanlış kelime | Ağır bağımlılık (TensorFlow) | Şimdilik dışarıda |
| Güçlü bulut modeli (API) | Kurulun yaptığı işi sistem içinde yapar | Hepsi | Ücretli, sayfalar dışarı gider | Kullanıcı kararı |
| Organik veriyle Türkçe GEC (arXiv 2405.15320) | 2,3 milyon cümlelik dilbilgisi düzeltme verisi ve modeli | Geçerli ama yanlış kelime | Eğitim gerekir | K33 deneyimi nedeniyle şimdilik dışarıda |
| NoisyWikiTr (2025) | Yapay yazım hatalı Vikipedi verisi | Yazım | — | Yapay hata: K33'te yapay veriyle eğitim gerçek kitapta başarısız oldu; dışarıda |

## Değerlendirme planı (K47, önerilen)

Her araç **ayarlanmadan**, ön kayıtlı bir eşikle, elimizdeki etiketli veride sınanır: K42 ve K45'in A sayfaları
(60 sayfa, kurulun bulduğu 44 gerçek hata, kurulun "hata değil" dediği adaylar). Bu sayfalar görülmüş olduğu
için sonuç ürünün başarısı değil, aracın denemeye değip değmediğidir. Geçen araç ürüne girerse etkisi yine yeni
kitapta ölçülür.

Ön kayıt örneği (her araç için ayrı): kendi sınıfındaki gerçek hataların en az yarısını bulmalı ve sayfa başına
1'den az yanlış işaret üretmeli; aksi hâlde araç kapatılır.

## Kaynaklar

- https://huggingface.co/ytu-ce-cosmos/turkish-base-bert-punctuation-correction
- https://arxiv.org/abs/2412.02698 (Scaling BERT Models for Turkish Automatic Punctuation and Capitalization Correction)
- https://huggingface.co/uygarkurt/bert-restore-punctuation-turkish
- https://github.com/tdd-ai/hunspell-tr
- https://arxiv.org/abs/2403.01309 (VNLP: Turkish NLP Package)
- https://arxiv.org/abs/2405.15320 (Organic Data-Driven Approach for Turkish Grammatical Error Correction and LLMs)
- https://peerj.com/articles/cs-2889/ (Leveraging large language models for spelling correction in Turkish, NoisyWikiTr)
- https://arxiv.org/abs/2309.11346 (GECTurk)
