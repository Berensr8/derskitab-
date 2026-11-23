# Bağımsız Değerlendirme 4 (K49) — Ön Kayıt ve Kilitli Sayfalar

- **Tarih:** 2026-11-23
- **Amaç:** K48'de ürüne eklenen sayfa okumanın (yerel dil modeli `gemma4:12b-it-qat` her sayfayı okuyup yazım ve
  noktalama önerisi verir) geliştirme verisinde görülen etkisini (44 gerçek hatadan bulunan 15 → 26) geliştirmede
  hiç kullanılmamış iki yeni kitapta, K42/K45 ile aynı bağımsız kurul yöntemiyle ölçmek. Aynı ölçüm, ürünün
  bütününün (K46 değişiklikleri dahil) yeni kitaplardaki isabetini ve bulma oranını da verir.
- **Ölçülen ürün kodu:** `68a7a71` (ürün kodu ölçüm boyunca dondurulmuştur; `derskitabi/` değişmez)
- **Ürün ayarı:** ürünün varsayılanı: yazım hakemi açık, sayfa okuma açık (Ollama ve gemma4 hazır).
- **Rastgelelik tohumu:** `20261123`
- **Kilitli havuz dosyası:** `veri/bagimsiz4/havuz.json` (git dışında, LF satır sonu)
- **SHA-256 parmak izi:** `8b15506e0e960635fffd7285f56f0d63697e30983a1aa09f4eee6c3ec166bebd`
- **Bu belge, sistem bu iki kitapta hiç çalıştırılmadan önce yazılıp commit edilmiştir.** Claude kitapların metnini
  okumamıştır; yalnız sayfa ve blok sayılarına bakılmıştır.

---

## 1. Yeni Kitaplar

Kullanıcı onayıyla 2026-11-23'te MEB OGM Materyal'den (ogm-large-cdn.eba.gov.tr) indirildi. İki ders de
(Tarih, Coğrafya) projede daha önce hiç kullanılmadı.

| Dosya | Kitap | PDF Sayfa | Metinli Sayfa | Blok | PDF SHA-256 (ilk 16) | Bloklar SHA-256 (ilk 16) |
|---|---|---:|---:|---:|---|---|
| `veri/tarih9.pdf` | Tarih 9 | 264 | 262 | 7.416 | `9ab184314386777d` | `0116451c7dec15b2` |
| `veri/cografya9.pdf` | Coğrafya 9 | 244 | 242 | 12.674 | `3aa58c1f46af9072` | `fc15704ec769276f` |

Bloklar `.venv` (PyMuPDF 1.28.2) ile `python -m derskitabi.pdf_cikarma` komutuyla çıkarıldı.

---

## 2. Ölçüm Yöntemi

K42/K45 ile aynı:
- **A (bulma oranı):** ChatGPT ve Gemini, kilitli 30 A sayfasını baştan sona okuyarak sistemden bağımsız olarak
  yazım ve noktalama hatalarını çıkarır (`testseti/bagimsiz/A_talimat.txt` değiştirilmeden).
- **Karar kurulu:** ChatGPT, Gemini ve DeepSeek bütün adayları oylar (`KURUL_talimat.txt` şablonu değiştirilmeden).
  Adaylar karışık sırada, nötr kimlikle (`K001`…) sunulur; adayın kaynağı, güven puanı ve sistemin önerisi
  gösterilmez. Karar çoğunlukla (en az 2/3). Alıntı/replik/tarihî metindeki yazar veya dönem üslubu hata
  sayılmaz (MEB TYMM 2.4.1); dizgi bozulmaları hata sayılır.
- **Metin katmanı kontrolü (K41-ek):** adayın her sözcüğü sayfanın glif düzeyindeki karakterlerinde aranır;
  bulunamayan aday kurula gitmez, pay ve paydadan çıkarılıp ayrı raporlanır.
- **Eşleşme (bulma):** bir A hatası, sistemin aynı sayfada gösterdiği (güven ≥ 0,5) bir tespitle K42/K45'teki
  mekanik eşleşme kuralıyla eşleşirse "bulundu" sayılır.
- **Etiketi kim koymaz:** Claude ve öğrenci etiket koymaz; oylar mekanik olarak sayılır.

### K45'ten farklar (sebebiyle)

1. **Sayfa okuma katmanı ayrı örneklenir** (B2, aşağıda). Sebep: sayfa okumanın kendi isabeti bu ölçümün asıl
   sorusu; tek havuzdan 80 örnekte sayfa okuma payı küçük kalırsa isabeti ölçülemez.
2. **Hakemsiz ikincil ölçüm yapılmaz.** Sebep: ürünün varsayılanı hakemli; K45'te hakemin gizlediği 35 tespitin
   34'ü kurulda gerçekten "hata değil" çıktı, soru cevaplandı. Kurul yükü sayfa okuma örneğine aktarıldı.
3. **Kural listesine K46'nın `kesme_bosluk` kuralı eklendi.**

---

## 3. Kilitli Örneklem ve Havuz

`testseti/araclar/k49_havuz.py`, tohum `20261123`; seçim kuralı K42/K45 ile aynı (ilk ve son 10 sayfa hariç, en
az 150 kelime paragraf; uygun sayfa: Tarih 9'da 166, Coğrafya 9'da 159).

### A sayfaları (bulma oranı, 30 sayfa)
- **Tarih 9 (15):** 23, 39, 44, 47, 73, 79, 83, 116, 158, 161, 176, 200, 213, 221, 228
- **Coğrafya 9 (15):** 36, 37, 38, 40, 55, 84, 94, 107, 111, 122, 127, 173, 174, 177, 210

### B havuzu (isabet): A dışındaki bütün sayfalar
Tarih 9: 249 sayfa, Coğrafya 9: 229 sayfa; toplam 478 sayfa. Bu sayfalarda ürünün gösterdiği (güven ≥ 0,5)
benzersiz yazım tespitleri üç katmana ayrılır:

- **B1 — mevcut hat** (sayfa okuma dışındaki bütün gösterilen tespitler): 80'den fazlaysa tohum `20261123` ile
  rastgele 80.
- **B2 — sayfa okuma** (`alt_tur = sayfa_okuma`, gösterilen): 60'tan fazlaysa tohum `20261123:sayfa_okuma` ile
  rastgele 60.
- **B3 — kurallar:** K44'ün dokuz kuralı (`bitisik_rakam`, `yil_virgul_bosluk`, `liste_tutarsiz_virgul`,
  `iki_nokta_bosluk`, `yonerge_cift_nokta`, `yonerge_soru_isareti`, `bir_takim`, `birim_gr`, `yanlis_kelime`),
  `buyuk_harf_i` ve `kesme_bosluk`: B1'e girmemiş gösterilen tespitleri, kural başına en çok 10 (fazlaysa tohum
  `20261123:<alt_tur>` ile 10). B3 yalnız kural başına isabet için kullanılır, genel isabete katılmaz.

---

## 4. Ölçüler

- **İsabet (ürün, sayfa okuma dahil):** katmanlı tahmin `(N1·p1 + N2·p2) / (N1 + N2)`; N1, N2 B havuzundaki
  gösterilen tespit sayıları, p1, p2 B1 ve B2'nin kurul isabeti. Wilson %95 aralıkları katman başına ayrıca.
- **İsabet (sayfa okuma kapalı):** p1 (K45'in hakemli isabetiyle karşılaştırılabilir).
- **Sayfa okuma isabeti:** p2.
- **Bulma oranı:** A'daki gerçek hatalardan (kurulun HATA dediği, A okuyucularından gelen adaylar) ürünün
  gösterdiği tespitlerle eşleşenlerin oranı; sayfa okuma açık ve kapalı (aynı çıktıdan `sayfa_okuma`
  tespitleri çıkarılarak) ayrı ayrı. Sayfa okuma mevcut tespitlerin güvenini değiştirmediği için (K48 süzgeç 4)
  "kapalı" hâl bu çıkarmayla birebir elde edilir.
- **Sayfa başına sayfa okuma tespiti:** 478 B sayfasında gösterilen `sayfa_okuma` tespiti / 478.
- **Güven grupları:** B1'de güven 1,0 / 0,75 / 0,5 gruplarının isabeti.

---

## 5. Başarı Ölçütleri (sonradan değişmez)

1. **Ürün isabeti (sayfa okuma dahil) ≥ %35.**
2. **Bulma oranı (sayfa okuma açık) ≥ %30.**
3. **Sayfa okumanın katkısı:** sayfa okuma açıkken bulunan gerçek hata sayısı, kapalıyken bulunandan en az
   **3 fazla** ve en az **A'daki gerçek hata sayısının %10'u kadar** fazla.
4. **Sayfa okuma isabeti (p2) ≥ %30.**
5. **Öncelik sırası ters değil:** B1'de güven 1,0 grubunun isabeti 0,75 grubununkinden düşük değil (grup başına
   5'ten az tespit varsa "ölçülemedi").
6. **Kural başına isabet:** B3'te en az 3 tespiti olan her kuralın isabeti ≥ %50; altında kalan kural işaretlenir.

### Sonuca göre yapılacak (önceden sabit)

- **Ölçüt 3 ve 4 birlikte tutarsa:** sayfa okuma ürünün varsayılanında açık kalır.
- **Biri tutmazsa:** sayfa okuma kapalı varsayılana alınır, seçenek olarak kalır; arayüzde ölçülen isabeti ve
  katkısı yazılır.
- Sonuç ne olursa olsun ürün metinleri (`rapor.py` OLCULEN_BASARI, `arayuz/ozet.py` GUVEN) K49 sayılarıyla
  güncellenir. Ölçüt 6'da işaretlenen kurallar sonraki iş olarak yazılır; bu ölçümde ürün değişmez.

### Karşılaştırma

Sonuç belgesinde K42 (hakemli isabet 7/25, bulma 0/17), K45 (hakemli isabet 20/76 = %26,3, bulma 1/27 = %3,7)
ve K48 geliştirme (26/44, şişkin) yan yana verilir. Dersler ve sınıflar farklı olduğu için doğrudan
karşılaştırmanın sınırı yazılır.
