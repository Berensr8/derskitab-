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
| `testseti/` | Kilitli test setleri, sonuçları ve seti üreten betikler (K20) |
| `veri/` | İncelenecek kitap PDF'leri ve çıktılar (git'e eklenmez) |
| `belgeler/` | Proje tanımı ve ders belgeleri |

## Kullanım

**En kolay yol:** `DEMO.bat` dosyasına çift tıklayın (ya da bir PDF'i üzerine sürükleyin).
PDF seçilir, altı adım çalışır (PDF, okunabilirlik, yazım, bilgi tutarsızlığı, inceleme,
notlu PDF) ve inceleme sayfası tarayıcıda açılır. Çıktılar `veri/demo/<kitap adı>/` klasörüne yazılır.

- **Notlu PDF** (`<kitap>_notlu.pdf`): kitabın kendisi, tespitler üzerinde standart PDF yorum
  notu olarak (Acrobat, Edge, Foxit… her okuyucuda açılır; kitabın metni ve sayfa düzeni değişmez).
  Kırmızı dalgalı çizgi = yazım, turuncu çerçeve = dilsel karmaşıklık, mor vurgu = çelişen cümleler
  (kenardaki "↔ s. 45" etiketi karşı cümleye götürür). 1. sayfada özet notu; Yer İmleri panelinde
  kritere göre tespit listesi. Editör notlara yanıt yazabilir, "çözüldü" işaretleyebilir.

- **Bilgi tutarsızlığı** yerel modeller gerektirir. Kitabın önceden hesaplanmış tam kitap
  sonucu (`veri/<kitap>_tutarlilik_adaylar.json`) varsa o kullanılır; yoksa Ollama çalışıyorsa
  seçili sayfalarda çalıştırmak için sorulur; ikisi de yoksa adım atlanır.
- **Yazım hakemi:** Ollama hazırsa demo, kelime tespitlerinin dil modeline danışılmasını önerir;
  model "muhtemelen doğru" dediği tespitler (terim, alıntı) silinmez, soluk ve düşük öncelikli gösterilir.
- **Test modu:** test setinde maddesi olan kitaplarda (Sosyal Bilgiler 6, Biyoloji 10) demo,
  bilerek çelişki eklenmiş metinle bir inceleme de gösterebilir (gerçek kitaplarda çelişki
  bulunmadığı için özelliği göstermenin yolu). Eklenen cümleler sayfa görüntüsünde görünmez.
- Uzun yerel model işlerinden önce: bilgisayarı şarja takın, Ollama'yı `OLLAMA_BASLAT.bat`
  ile başlatın (ekran kartında pay bırakır).

Adımlar tek tek de çalıştırılabilir:

```bash
# 1. PDF'ten blokları çıkar -> veri/kitap_bloklar.json
.venv\Scripts\python.exe -m derskitabi.pdf_cikarma veri\kitap.pdf

# 2. Okunabilirlik -> veri/kitap_okunabilirlik_ozet.json, _tespitler.json
.venv\Scripts\python.exe -m derskitabi.kriterler.okunabilirlik veri\kitap_bloklar.json

# 3. Yazım (Starlang + Zemberek, TDK kuralları) -> veri/kitap_yazim_tespitler.json
.venv\Scripts\python.exe -m derskitabi.kriterler.yazim veri\kitap_bloklar.json
#    --hakem: kelime tespitleri yerel dil modeline danışılır (Ollama); terim ve alıntılar
#    silinmez, düşük önceliğe iner (K25)
.venv\Scripts\python.exe -m derskitabi.kriterler.yazim veri\kitap_bloklar.json --hakem

# 4. Bilgi tutarsızlığı (bge-m3 + gemma4 + Turkish-Gemma, Ollama ile yerel; önce: ollama serve)
#    -> veri/kitap_tutarlilik_tespitler.json (+ _adaylar.json: her aday çiftin kararları)
.venv\Scripts\python.exe -m derskitabi.kriterler.tutarlilik veri\kitap_bloklar.json

# Notlu PDF (editör için): tespitler kitabın PDF'ine yorum notu olarak -> veri/kitap_notlu.pdf
#    Tutarlılık sonucu varsa (veri/kitap_tutarlilik_tespitler.json) o da eklenir.
#    --dusuk-guven: hakemin "muhtemelen doğru" dediği yazım tespitleri de (gri) eklenir
.venv\Scripts\python.exe -m derskitabi.pdf_notlari veri\kitap.pdf --hakem

# Sistemin gözünden PDF (geliştirici için): bloklar, cümleler ve tespitler kitabın üzerine çizilir
.venv\Scripts\python.exe -m derskitabi.gorsellestir veri\kitap.pdf --sayfalar 28-35

# Etkileşimli inceleyici (tarayıcıda açılan tek HTML dosyası): bloğa tıkla, ayrıntıyı gör;
# "Yazım denetimi" sekmesi her kelimede iki aracın kararını ve atlanma sebebini gösterir,
# "Tutarlılık" sekmesi karşılaştırılan cümleleri ve modellerin gerekçesini gösterir
.venv\Scripts\python.exe -m derskitabi.inceleyici veri\kitap.pdf --sayfalar 13-32

# Test modu: bilerek çelişki eklenmiş metinle (önce değerlendirme çalıştırılmış olmalı)
.venv\Scripts\python.exe -m derskitabi.inceleyici veri\kitap.pdf --test-modu

# Değerlendirme: kilitli test setleri; ayar yaparken yalnız geliştirme seti
# (sonuçlar: testseti/*_sonuclari.md)
.venv\Scripts\python.exe -m derskitabi.degerlendirme_yazim --set gelistirme --hakem
.venv\Scripts\python.exe -m derskitabi.degerlendirme_okunabilirlik
# Tutarlılık (K20)
.venv\Scripts\python.exe -m derskitabi.degerlendirme --set gelistirme
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
