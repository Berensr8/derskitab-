# Ders Kitaplarında İçerik ve Tutarlılık Hatalarının Otomatik Tespiti

PDF formatındaki Türkçe ders kitaplarını üç kritere göre inceleyen sistem
(OMÜ Yazılım Geliştirme I dersi projesi).

1. **Yazım ve dil hataları** — kural tabanlı
2. **Yaş/sınıf seviyesine uygunluk** — okunabilirlik formülleri
3. **Bilgi tutarsızlığı** — LLM tabanlı, aynı kitap içindeki çelişkiler

Her tespit için sayfa, paragraf (blok) ve açıklama gösterilir.

## Klasör yapısı

| Klasör | İçerik |
|---|---|
| `derskitabi/` | Asıl kod: veri modeli, PDF çıkarma, kriterler, arayüz |
| `testler/` | Birim testleri |
| `degerlendirme/` | Test seti ve precision/recall betiği |
| `veri/` | İncelenecek kitap PDF'leri ve çıktılar (git'e eklenmez) |
| `belgeler/` | Proje tanımı ve ders belgeleri |

## Kullanım

**En kolay yol:** `DEMO.bat` dosyasına çift tıklayın (ya da bir PDF'i üzerine sürükleyin).
PDF seçilir, tüm adımlar çalışır ve inceleme sayfası tarayıcıda açılır. Çıktılar
`veri/demo/<kitap adı>/` klasörüne yazılır.

Adımlar tek tek de çalıştırılabilir:

```bash
# 1. PDF'ten blokları çıkar -> veri/kitap_bloklar.json
.venv\Scripts\python.exe -m derskitabi.pdf_cikarma veri\kitap.pdf

# 2. Okunabilirlik -> veri/kitap_okunabilirlik_ozet.json, _tespitler.json
.venv\Scripts\python.exe -m derskitabi.kriterler.okunabilirlik veri\kitap_bloklar.json

# 3. Yazım (Starlang + Zemberek, TDK kuralları) -> veri/kitap_yazim_tespitler.json
.venv\Scripts\python.exe -m derskitabi.kriterler.yazim veri\kitap_bloklar.json

# 4. Bilgi tutarsızlığı (bge-m3 + gemma4 + Turkish-Gemma, Ollama ile yerel; önce: ollama serve)
#    -> veri/kitap_tutarlilik_tespitler.json (+ _adaylar.json: her aday çiftin kararları)
.venv\Scripts\python.exe -m derskitabi.kriterler.tutarlilik veri\kitap_bloklar.json

# Sistemin gözünden PDF: bloklar, cümleler ve tespitler kitabın üzerine çizilir
.venv\Scripts\python.exe -m derskitabi.gorsellestir veri\kitap.pdf --sayfalar 28-35

# Etkileşimli inceleyici (tarayıcıda açılan tek HTML dosyası): bloğa tıkla, ayrıntıyı gör;
# "Yazım denetimi" sekmesi her kelimede iki aracın kararını ve atlanma sebebini gösterir
.venv\Scripts\python.exe -m derskitabi.inceleyici veri\kitap.pdf --sayfalar 13-32
```

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Bilgi tutarsızlığı için [Ollama](https://ollama.com) ve modeller (~15 GB):

```bash
ollama pull bge-m3
ollama pull gemma4:12b-it-qat
ollama pull hf.co/ytu-ce-cosmos/Turkish-Gemma-9b-T1-GGUF:Q4_K_M
```
