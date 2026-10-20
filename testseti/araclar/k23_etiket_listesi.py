"""K23/K25 precision için etiketlenecek tespitleri bağlamlarıyla listeler.

Geliştirme (K23): Sosyal Bilgiler 6'nın bütün yazım tespitleri + Biyoloji 10'dan 50 tespit.
Test (K25, --test): Matematik 11 ve TDE 9'dan 40'ar tespit — yazım hakemi (dil modeli)
çalıştırılmadan ÖNCE etiketlendi (etiketler modelin kararından etkilenmesin).
Çıktı: testseti/yazim_etiket_listesi[_test].json (etiketler: yazim_etiketler[_test].json)
"""
import json
import random
import sys
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")
TEST = "--test" in sys.argv
ORNEKLEM = {"matematik11": 40, "turkdili9": 40} if TEST else {"kitap": None, "biyoloji10": 50}  # None = hepsi
TOHUM = 20261020
ON_EK = {"kitap": "ES", "biyoloji10": "EB", "matematik11": "TM", "turkdili9": "TT"}

liste = []
for kitap, n in ORNEKLEM.items():
    tespitler = json.loads((PROJE / "veri" / f"{kitap}_yazim_tespitler.json").read_text(encoding="utf-8"))
    bloklar = {(b["sayfa_no"], b["blok_no"]): b["metin"] for b in
               json.loads((PROJE / "veri" / f"{kitap}_bloklar.json").read_text(encoding="utf-8"))}
    secilen = tespitler if n is None else random.Random(TOHUM).sample(tespitler, n)
    secilen = sorted(secilen, key=lambda t: (t["sayfa_no"], t["blok_no"]))
    for i, t in enumerate(secilen, 1):
        metin = bloklar[(t["sayfa_no"], t["blok_no"])]
        yer = max(0, metin.find(t["metin_parcasi"]))
        liste.append({"id": f"{ON_EK[kitap]}{i:02d}", "kitap": kitap,
                      "sayfa_no": t["sayfa_no"], "blok_no": t["blok_no"], "alt_tur": t["alt_tur"],
                      "guven": t["guven_skoru"], "parca": t["metin_parcasi"],
                      "baglam": metin[max(0, yer - 70):yer + len(t["metin_parcasi"]) + 70]})
(PROJE / "testseti" / f"yazim_etiket_listesi{'_test' if TEST else ''}.json").write_text(json.dumps(liste, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
for x in liste:
    print(f"{x['id']} s{x['sayfa_no']} {x['alt_tur'][:5]} {x['guven']} [{x['parca']}] … {x['baglam']}")
