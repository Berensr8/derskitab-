# K43: Sayfayı Yerel Modele Okutma Denemesi — Ön Kayıt

- **Tarih:** 2026-11-15
- **Amaç:** Yerel dil modelinin (`gemma4:12b-it-qat`) bir ders kitabı sayfasını baştan sona okuyarak, mevcut kural ve morfoloji denetiminin yakalayamadığı hataları makul sayıda yanlış alarmla önerip öneremediğini sınamak (fizibilite denemesi).
- **Kapsam:** Ürün koduna (`derskitabi/`) dokunulmaz. Bu 30 sayfa (`bagimsiz_degerlendirme2/A_30_sayfa_metin.txt`, S01–S30) daha önce K42'de görülmüştür; sonuç ürünün başarısı değil, bu yolun açık olup olmadığıdır.

---

## 1. Model ve Çağrı Yapılandırması

- **Model:** `gemma4:12b-it-qat` (`derskitabi.yerel_model.sohbet` üzerinden)
- **Sıcaklık (`temperature`):** `0`
- **Bağlam penceresi (`num_ctx`):** `4096` (sayfa metni 4000 karakteri aşarsa paragraf sınırından `\n\n` bölünerek ayrı isteklerle gönderilir)
- **Azami üretim (`num_predict`):** `1024`
- **JSON Çıktı Şeması (`ozellikler`):**
  ```json
  {
    "hatalar": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "kitaptaki": {"type": "string"},
          "onerilen": {"type": "string"},
          "gerekce": {"type": "string"}
        },
        "required": ["kitaptaki", "onerilen", "gerekce"]
      }
    }
  }
  ```

### Sistem İstemi (`SISTEM`) — Tam Metin

```text
Sen Türkçe ders kitapları için çalışan bir yazım editörüsün. Bu ders kitabı sayfasında yazım, noktalama, dizgi ve yanlış kullanılmış kelime hatalarını bul. Eski metin alıntılarını, şiirleri ve ağız özelliklerini hata sayma. Her hata için kitaptaki hâlini, önerini ve kısa gerekçeni ver. Emin değilsen yazma. Sayfada hata yoksa boş liste döndür.
```

### Soru Şablonu (`SORU_SABLONU`) — Tam Metin

```text
Kitap ve sayfa: {baslik}

Sayfa metni:
{metin}
```

---

## 2. Eşleşme Kuralı (Mekanik Sayım)

- **Gerçek Hata Zemini:** K42 bağımsız kurulunun 30 A sayfasındaki 82 aday arasından çoğunluk oyuyla (`HATA`) belirlediği **17 gerçek hata** (`veri/bagimsiz2/A_birlesik_anahtar.json`, `kurul_anahtar.json`, `kurul_sonuc.json`).
- **Normalleştirme:** Karşılaştırma öncesinde metin Türkçe küçük harfe (`tr_kucuk`) çevrilir, kıvrık kesme/tırnak işaretleri düzleştirilir ve tüm boşluklar kaldırılır (`re.sub(r"\s+", "", ...)`). Aday açıklamasındaki parantez içi ek notlar (ör. `göktaşını (ve göktaşından)` -> `göktaşını`) karşılaştırmada hem tam hâliyle hem parantez öncesi asıl parçayla kontrol edilir.
- **Eşleşme Şartı:** Modelin bir önerisi (`kitaptaki` alanı boş olmayan ve en az 2 karakter içeren), aynı sayfadaki (`S01`–`S30`) bir gerçek hatayla ancak şu durumda eşleşmiş sayılır:
  - Normalleştirilmiş öneri `kitaptaki` metni, gerçek hatanın normalleştirilmiş `kitaptaki` metnini içeriyorsa **ya da** gerçek hatanın normalleştirilmiş `kitaptaki` metni önerinin normalleştirilmiş `kitaptaki` metnini içeriyorsa.
- Tüm eşleşmeler elle değil `testseti/araclar/k43_say.py` betiğiyle mekanik olarak sayılır.

---

## 3. Başarı Ölçütü ve Karar Kuralı

- **Devam:** Model 17 gerçek hatanın **en az 9'unu** öneriyor ($\ge 9/17$) **ve** sayfa başına ortalama **5'ten az** aday üretiyor ($< 5,0$ aday/sayfa, yani 30 sayfada toplam $< 150$ aday).
- **Kapat:** Model 17 gerçek hatanın **8'ini veya daha azını** öneriyor ($\le 8/17$).
- **Belirsiz:** Model 17 gerçek hatanın en az 9'unu öneriyor ($\ge 9/17$) **ancak** sayfa başına ortalama **5 veya daha fazla** aday üretiyor ($\ge 5,0$ aday/sayfa).

İstem bu ön kayıt commit'inden sonra değiştirilmeyecektir.
