# Kesme işareti denetimi (K34) — sonuçlar

Yazım modeli (K33) ürüne giremedi ama kitaplarda bulduğu tek gerçek hata ("Türkistanda") sistemin hiç bakmadığı bir türdü: büyük harfle başlayan kelimeler denetlenmiyordu, kesme işareti kuralı yoktu. TDK "Kesme İşareti" sayfasına göre dört kural yazıldı (`derskitabi/kriterler/kesme.py`):

| Kural | Örnek |
|---|---|
| Özel ada gelen iyelik, durum, bildirme eki | Türkistanda → Türkistan'da, Anadoluya → Anadolu'ya |
| Kısaltmaya gelen ek | DNAnın → DNA'nın |
| Sayıya gelen ek | 1923te → 1923'te |
| Gereksiz kesme (yapım eki, çokluk eki, dil adı) | Mora'lı → Moralı, Osmanlılar'ın → Osmanlıların, Türkçe'ye → Türkçeye |

Özel adı Zemberek tanır. Kurum adları ("Türk Dil Kurumundan" doğru), cins ad okuması olan kelimeler ("Doğuda") ve çokluk/yapım ekleri ("Türklerin", "Konyalı") TDK istisnası olarak atlanır. Zemberek'in sözlüğünde garip özel adlar olduğu için ("Karekod", "Akti", "Buyru") **kitap aynı adı başka bir yerde kesmeyle yazmış olmalı**: tespit hem TDK'ya hem kitabın kendi yazımına aykırıdır.

Ölçüt ve karar kuralı doğrulamadan önce yazıldı (KARARLAR K34, commit 37ce3a9).

## Doğrulama (görülmemiş sayfalar: TDE 10 tamamı + diğer kitapların test sayfaları)

105 aday kaynağı gizli olarak etiketlendi (`kesme_etiketler.json`).

| Kaynak | Gerçek / toplam | İsabet |
|---|---|---|
| **Kural, toplam** | 31 / 46 | **0,67** |
| Özel ad + ek | 14 / 17 | 0,82 |
| Gereksiz kesme | 17 / 28 | 0,61 |
| Sayı + ek | 0 / 1 | — |
| Yazım modeli (K33) önerileri, kuralın bulmadıkları | 10 / 59 | 0,17 |

**Karar:** kural 0,50–0,70 aralığında → ürüne **güven 0,5 (orta öncelik)** ile girdi. Model önerileri < 0,50 → girmedi.

Kuralın sahte tespitleri: eski metin aktarımı 7 ("İbrâhim Paşa’ların, Viyana Sefîri…"), adı "-ce" ile biten kişi 4 ("Meryemce’nin" — dil adı sanıldı), "Ömerî" 3 (şapkalı "î" ek sanıldı — doğrulamadan sonra düzeltildi; resmî sonuç değişmedi), üs/PDF okuma 1.

**Yapay recall:** doğrulama sayfalarındaki 3.095 doğru "Ad’ek" yazımından kesme silinince kural 856'sını buldu (%28). Kaçanlar: kitapta hiç kesmeyle yazılmamış adlar, Zemberek'in cins ad olarak da okuduğu adlar (Fatih, Doğu), çok kelimeli adlar ("Kurtuluş Savaşına"). Bilerek temkinli: az ama isabetli.

## Ürün

9 kitabın tamamında 51 tespit (gereksiz kesme 29, özel ad 21, sayı 1). En çok Türk Dili ve Edebiyatı kitaplarında; Biyoloji kitaplarında hiç yok. Ölçülen isabetle bunların ~34'ü, sistemin önceden hiç göremediği gerçek hatalar.
