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

```bash
# 1. PDF'ten blokları çıkar -> veri/kitap_bloklar.json
.venv\Scripts\python.exe -m derskitabi.pdf_cikarma veri\kitap.pdf

# 2. Okunabilirlik -> veri/kitap_okunabilirlik_ozet.json, _tespitler.json
.venv\Scripts\python.exe -m derskitabi.kriterler.okunabilirlik veri\kitap_bloklar.json

# Sistemin gözünden PDF: bloklar, cümleler ve tespitler kitabın üzerine çizilir
.venv\Scripts\python.exe -m derskitabi.gorsellestir veri\kitap.pdf --sayfalar 28-35
```

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
