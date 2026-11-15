# K45: Bağımsız değerlendirme 3 (yeni kitaplarda K44'ün gerçek etkisi)

K44 iyileştirmeleri (commit `ba44473`) geliştirme verisinde isabeti 7/25'ten 7/16'ya, bulma oranını 0/17'den
9/17'ye çıkardı. Bu sayılar şişkin: kurallar o hatalara bakılarak yazıldı. Bu görev aynı yöntemi (K42) **hiç
kullanılmamış iki kitapta** tekrarlar.

Yeni kitaplar (kullanıcı onayıyla 2026-11-15'te MEB OGM Materyal'den indirildi; Claude yalnız sayfa sayısına ve
parmak izine baktı, metnini okumadı):

| Dosya | Kitap | Sayfa | SHA-256 (ilk 16) |
|---|---|---|---|
| `veri/biyoloji12.pdf` | Biyoloji 12 | 213 | `1f0a78b8d035d330` |
| `veri/inkilap12.pdf` | T.C. İnkılâp Tarihi ve Atatürkçülük 12 | 287 | `64a392e28af85a93` |

## Kurallar (değişmez)

- Komutları her zaman `D:\derskitabı\.venv\Scripts\python.exe` ile çalıştır (PyMuPDF 1.28.2).
- **Ürün kodu dondurulmuştur.** Ölçülen sürüm `ba44473`. `derskitabi/` içinde hiçbir değişiklik yapma; bir hata
  bulursan dur ve bildir. Yeni kod yalnız `testseti/araclar/k45_*.py`. K42 betiklerini (`k42_*.py`) yeniden kullan,
  gerekirse parametreleştir; K42 sonuçlarını değiştirme.
- Kurul talimatlarını (`testseti/bagimsiz/A_talimat.txt`, `KURUL_talimat.txt` şablonu) değiştirme.
- Bu iki kitabın metnini geliştirme amacıyla okuma, örnek arama, kural deneme. Yalnız aşağıdaki adımlar.
- Hiçbir şey indirme. Kullanıcının uygulamalarını kapatma, sistem ayarlarını değiştirme. GPU meşgulse dur ve bildir.
- Commit: küçük, Türkçe, `git commit -F <dosya>`. PowerShell `Set-Content` kullanma. Her commit şu satırla biter:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push yapma.
- Sayıları olduğu gibi yaz. Ölçüt tutmazsa sonuç budur.

## Aşama 1 (bu oturumda): ön kayıt, kilit, paketler

### 1.1 Bloklar

İki kitabın bloklarını .venv ile çıkar (`veri/biyoloji12_bloklar.json`, `veri/inkilap12_bloklar.json`).
Yalnız sayı raporla (sayfa, blok); metne bakma.

### 1.2 Ön kayıt ve sayfa kilidi (sistem çalıştırılmadan önce, ayrı commit)

`testseti/k45_on_kayit.md`:

- **Tohum:** `20261116`.
- **A sayfaları (bulma oranı):** her kitaptan 15, toplam 30. K42 ile aynı uygunluk: ilk ve son 10 sayfa hariç,
  en az 150 kelime paragraf.
- **B (isabet):** iki kitabın A dışındaki **bütün** sayfalarında hakemli sistemin gösterdiği (güven ≥ 0,5) yazım
  tespitlerinin tamamı. 80'den fazlaysa tohumla rastgele 80 seçilir. Ayrıca K44'ün dokuz kuralının
  (`bitisik_rakam`, `yil_virgul_bosluk`, `liste_tutarsiz_virgul`, `iki_nokta_bosluk`, `yonerge_cift_nokta`,
  `yonerge_soru_isareti`, `bir_takim`, `birim_gr`, `yanlis_kelime`) ve `buyuk_harf_i`'nin bütün tespitleri,
  80'e girmeseler de eklenir (kural başına en çok 10). Hakemsiz sonuç ikincil olarak aynı yöntemle verilir.
- **Yöntem:** K42 ile birebir (A: ChatGPT ve Gemini sayfaları okur; kurul: ChatGPT, Gemini, DeepSeek, çoğunluk
  ≥ 2/3; adaylar karışık sırada ve nötr kimlikle; metin katmanı kontrolü K41-ek kuralıyla).
- **Başarı ölçütleri (sonradan değişmez):**
  1. Hakemli isabet **≥ %35**.
  2. Bulma oranı (gösterilen) **≥ %30**.
  3. Öncelik sırası ters değil: güven 1,0 grubunun isabeti, güven 0,75 grubununkinden düşük değil
     (grup başına 5'ten az tespit varsa "ölçülemedi" yazılır).
  4. K44 kurallarından en az 3 tespiti olan her birinin isabeti ≥ %50; altında kalan kural sonuç belgesinde
     işaretlenir (ürün değişikliği bu görevde yapılmaz).
- **Karşılaştırma:** K42 sonuçları (hakemli 7/25, bulma 0/17) ve K44 geliştirme sonuçları yan yana verilecek; yeni
  kitaplar farklı dersler olduğu için doğrudan karşılaştırmanın sınırı yazılacak.
- Havuz dosyasını (`veri/bagimsiz3/havuz.json`) LF ile yaz, SHA-256'sını ön kayda yaz.

Commit et. **Sonra** sistemi çalıştır.

### 1.3 Sistem çıktısının kilidi (ayrı commit)

- İki kitapta ürünü varsayılan ayarlarla (hakemli ve hakemsiz) çalıştır, çıktıyı `veri/bagimsiz3/` altına kaydet.
- B listesini ve A sayfalarındaki sistem tespitlerini (gizli anahtar) oluştur; parmak izlerini
  `testseti/bagimsiz3_kilit.txt`'ye yaz. Metin katmanı kontrolünü uygula.
- Commit et.

### 1.4 Kullanıcı paketi

`bagimsiz_degerlendirme3/` klasörü, K42'deki `bagimsiz_degerlendirme2/` ile aynı yapıda: `A_30_sayfa.pdf`
(sol üstte kırmızı kod S01…S30), `A_30_sayfa_metin.txt`, `A_talimat.txt`, `A_sayfa_listesi.json` ve kullanıcı için
`NASIL.md` (K42'deki gibi sade Türkçe, adım adım). Bu klasör git dışında kalır.

**Burada dur ve raporla:** sayfa listeleri, B tespit sayısı (hakemli/hakemsiz, kural başına), commit'ler.
Kullanıcı A cevaplarını getirince Aşama 2'ye geçilir.

## Aşama 2 (kullanıcı A cevaplarını getirince)

1. A cevaplarını birleştir (`k42_a_birlestir.py` mantığı), kurul listesini hazırla (`KURUL_talimat.txt`),
   kullanıcıya ver. Dur.
2. Kurul cevapları gelince oyları say (`k42_oyla.py` mantığı): isabet (hakemli, hakemsiz, Wilson %95), bulma oranı,
   güven grubu tablosu, kural başına isabet, Fleiss κ, kitap başına sonuçlar.
3. `testseti/bagimsiz3_sonuclari.md`: ön kayıt ölçütleri tablosu (tuttu/tutmadı), sonuçlar, kaçan hataların
   türleri, sınırlamalar. Commit et.
4. **Ürün metinlerine (`rapor.py` OLCULEN_BASARI, `arayuz/ozet.py` GUVEN) dokunma.** Claude sonuçları doğruladıktan
   sonra ayrı bir adımda güncellenecek.

## Raporda istenenler (her aşama sonunda)

1. Commit'ler.
2. Sayılar (aşamaya göre).
3. Ön kayıttan sapma (varsa, sebebiyle).
4. Teknik sorunlar.
