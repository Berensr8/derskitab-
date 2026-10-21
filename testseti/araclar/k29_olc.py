"""K29 ölçümü: kitap ipuçlarının (PDF okuma parçası, terim, alıntı) etiketli tespitler üzerindeki etkisi.

Etiketli her tespite (geliştirme: K23 ve K25 etiketleri; test: K29 körlemesine etiketler, bir kez)
ipuçları uygulanır; etiket türüne göre kaçının düşük önceliğe indiği ve indirme sebebi sayılır.
Gerçek hata hiç inmemeli.
Kullanım: python testseti/araclar/k29_olc.py [--test]
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJE))
from derskitabi.degerlendirme import set_yukle  # noqa: E402
from derskitabi.kayit import bloklari_yukle  # noqa: E402
from derskitabi.kriterler import dusuk_oncelik  # noqa: E402
from derskitabi.model import Tespit  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
TEST = "--test" in sys.argv
K29_KILIT = "2ec2e20ff30e2905455c2407f261934189af40717bd5f99552e78c73f5f6db18"
if TEST:
    etiketler = set_yukle(PROJE / "testseti" / "yazim_etiketler_k29.json", kilit=K29_KILIT)
else:
    etiketler = [x for ad in ("yazim_etiketler.json", "yazim_etiketler_test.json")
                 for x in json.loads((PROJE / "testseti" / ad).read_text(encoding="utf-8"))]

toplam = defaultdict(Counter)
inen_gercek, kalan_sahte = [], defaultdict(list)
for kitap in sorted({x["kitap"] for x in etiketler}):
    e = [x for x in etiketler if x["kitap"] == kitap]
    bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
    ts = [Tespit(x["sayfa_no"], x["blok_no"], (0, 0, 1, 1), "yazim", "", x["guven"],
                 alt_tur=x["alt_tur"], metin_parcasi=x["parca"]) for x in e]
    ts = dusuk_oncelik.isaretle(PROJE / "veri" / f"{kitap}.pdf", bloklar, ts)
    for x, t in zip(e, ts):
        tur = x["sebep"] or x["etiket"]
        s = dusuk_oncelik.sebep(t)
        toplam[tur][s or "-"] += 1
        toplam[f"[{kitap}] {x['etiket']}"]["indi" if s else "gösterilir"] += 1
        if s and x["etiket"] == "gercek":
            inen_gercek.append((x["id"], x["parca"], t.aciklama[-160:]))
        if not s and x["etiket"] == "sahte":
            kalan_sahte[tur].append(f"{x['parca']}")
        if "birleşince" in t.aciklama and not s:
            print("  birleşik yazım notu:", x["id"], x["parca"], "|", x["etiket"])

for tur, c in sorted(toplam.items()):
    print(f"{tur:28}", dict(c))
print("Düşük önceliğe inen GERÇEK hata:", inen_gercek or "yok")
for tur, v in kalan_sahte.items():
    print(f"Gösterilmeye devam eden sahte ({tur}, {len(v)}):", ", ".join(v[:40]))
