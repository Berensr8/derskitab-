"""K28 v2 ölçümü: alıntı ayırmanın TDE 11 körlemesine etiketleri üzerindeki sonucu.

Etiketler (testseti/alinti_etiketler_test.json) v2 yazılmadan önce kilitlendi (commit cbe1a92).
Kullanım: python testseti/araclar/k28_alinti_olc.py
"""
import sys
from collections import Counter
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJE))
from derskitabi.degerlendirme import set_yukle  # noqa: E402
from derskitabi.kayit import bloklari_yukle  # noqa: E402
from derskitabi.kriterler import alinti  # noqa: E402

KILIT = "0bf3d3c4200ec457362bd443c9a0e7151982afd8d8ef3fe21add11e988a10b42"

sys.stdout.reconfigure(encoding="utf-8")
etiketler = set_yukle(PROJE / "testseti" / "alinti_etiketler_test.json", kilit=KILIT)
bloklar = bloklari_yukle(PROJE / "veri" / "turkdili11_bloklar.json")
al = alinti.alinti_bloklari(bloklar, alinti.blok_bicimleri(PROJE / "veri" / "turkdili11.pdf", bloklar))
sayac = Counter((e["etiket"], (e["sayfa_no"], e["blok_no"]) in al) for e in etiketler)
for etiket in ("alinti", "alinti_kelime", "kitap_metni"):
    n = sayac[(etiket, True)] + sayac[(etiket, False)]
    print(f"{etiket:14}: {sayac[(etiket, True)]}/{n} düşük önceliğe indi")
gercek = [e for e in etiketler if e["gercek_hata"]]
print(f"gerçek hata: {sum((e['sayfa_no'], e['blok_no']) in al for e in gercek)}/{len(gercek)} kaybedildi")
sahte = [e for e in etiketler if not e["gercek_hata"]]
print(f"Gösterilen sahte tespit: {len(sahte)} → {sum((e['sayfa_no'], e['blok_no']) not in al for e in sahte)}")
print("Kaçan alıntılar:", [(e["id"], e["sayfa_no"], e["parca"]) for e in etiketler
                          if e["etiket"] == "alinti" and (e["sayfa_no"], e["blok_no"]) not in al])
