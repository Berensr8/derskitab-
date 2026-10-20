import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
veri = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
AD = {"kitap": "Sosyal Bilgiler 6", "biyoloji10": "Biyoloji 10"}
TUR = {"tarih": "tarih", "sayi": "sayı", "isim": "isim", "en_ilk": "en/ilk", "sozel": "sözel"}
s = ["# Tutarlılık test seti (K20) — KİLİTLİ", "",
     "Her satır kitaba bilerek eklenecek bir çelişki. **Kaynak** kitabın kendi (değişmeyen) ifadesi; "
     "**Değişiklik** bizim eklediğimiz/değiştirdiğimiz yer. Sayfa numaraları PDF sayfasıdır.", "",
     "- **tekrar boz:** kitabın zaten tekrar ettiği bir bilginin bir geçişindeki değer değiştirildi.",
     "- **yeniden yaz:** bilgi başka kelimelerle ve yanlış değerle yazılıp aynı konudaki başka bir paragrafın sonuna eklendi "
     "(paragraf otomatik seçildi: konuca en yakın, kaynaktan ≥3 sayfa uzak, etkinlik/soru değil).",
     "- **Set:** G = geliştirme (ayar yaparken bakılabilir), T = kilitli test (yalnız en sonda bir kez).", "",
     "- **Konum:** *etkinlik metni* = kaynak ya da hedef, bir etkinliğin okuma metninde/maddesinde (kitabın doğru diye "
     "sunduğu metin; bilerek yanlış yazılmış doğru-yanlış maddeleri ve test şıkları sete alınmadı). Sonuçlar ayrı raporlanır.", "",
     "**Kilit:** Set 2026-10-20'de kilitlendi; SHA-256 özeti KARARLAR.md'de (K20 eki). Test (T) maddelerine yalnız "
     "en sonda bir kez bakılır; ayarlar yalnız geliştirme (G) maddeleriyle yapılır. Gözden geçirmeyi kullanıcının "
     "isteğiyle Claude yaptı (ayrıntı KARARLAR.md).", ""]
for kitap in AD:
    s += [f"## {AD[kitap]}", "", "| No | Set | Tür | Yöntem | Konum | Kaynak (değişmiyor) | Değişiklik |", "|---|---|---|---|---|---|---|"]
    for o in veri:
        if o["kitap"] != kitap:
            continue
        kay = "<br>".join(f"s.{k['sayfa_no']}: …{k['parca']}…" for k in o["kaynaklar"])
        h = o["hedef"]
        if h["islem"] == "degistir":
            deg = f"s.{h['sayfa_no']}: ~~{h['eski']}~~ → **{h['yeni']}**"
        else:
            deg = f"s.{h['sayfa_no']} paragraf sonuna: **{h['yeni']}**<br><sub>(paragraf: {h['hedef_paragraf_basi'][:70]}…)</sub>"
        s.append(f"| {o['id']} | {'G' if o['set'] == 'gelistirme' else 'T'} | {TUR[o['tur']]} | "
                 f"{'tekrar boz' if o['yontem'] == 'tekrar_boz' else 'yeniden yaz'} | {'etkinlik metni' if o['konum'] == 'etkinlik_metni' else 'düz metin'} | {kay} | {deg} |".replace("\n", " "))
    s.append("")
Path(sys.argv[2]).write_text("\n".join(s), encoding="utf-8")
print("yazıldı")
