"""K29 körlemesine yazım etiketleri: Faz 2 kapanış işleri (PDF parçası, terim, alıntı v3) için.

Biyoloji 9, Biyoloji 11 ve TDE 12'nin (hiç geliştirme verisi olmamış kitaplar) yazım tespitlerinden
sabit tohumlu örneklem. K29 kodu yazılmadan ÖNCE etiketlenip kilitlenir (etiketler: k29_etiketle.py).
Tespitler o anki sistemle (alıntı ayırma ve hakem uygulanmadan) üretilir ve veri/ altına yazılır.
Çıktı: testseti/yazim_etiket_listesi_k29.json
"""
import json
import random
import sys
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJE))
from derskitabi.kayit import bloklari_yukle, tespitleri_kaydet  # noqa: E402
from derskitabi.kriterler import yazim  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ORNEKLEM = {"biyoloji9": 50, "biyoloji11": 50, "turkdili12": 80}
TOHUM = 20261021
ON_EK = {"biyoloji9": "B9", "biyoloji11": "B11", "turkdili12": "T12"}


def gorunur(s: str) -> str:
    """Özel kullanım alanındaki (PDF yazı tipine özgü) karakterleri görünür yazar."""
    return "".join(f"<U+{ord(c):04X}>" if 0xE000 <= ord(c) <= 0xF8FF or c == "�" else c for c in s)


liste = []
for kitap, n in ORNEKLEM.items():
    bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
    tespitler = yazim.analiz_et(bloklar)
    tespitleri_kaydet(tespitler, PROJE / "veri" / f"{kitap}_yazim_tespitler.json")
    metin = {(b.sayfa_no, b.blok_no): b.metin for b in bloklar}
    secilen = sorted(random.Random(TOHUM).sample(tespitler, n), key=lambda t: (t.sayfa_no, t.blok_no))
    for i, t in enumerate(secilen, 1):
        m = metin[(t.sayfa_no, t.blok_no)]
        yer = max(0, m.find(t.metin_parcasi))
        liste.append({"id": f"{ON_EK[kitap]}-{i:02d}", "kitap": kitap, "sayfa_no": t.sayfa_no,
                      "blok_no": t.blok_no, "alt_tur": t.alt_tur, "guven": t.guven_skoru,
                      "parca": t.metin_parcasi, "baglam": gorunur(m[max(0, yer - 90):yer + len(t.metin_parcasi) + 90]),
                      "onceki_blok": gorunur(metin.get((t.sayfa_no, t.blok_no - 1), "")[-80:]),
                      "sonraki_blok": gorunur(metin.get((t.sayfa_no, t.blok_no + 1), "")[:80])})
    print(kitap, len(tespitler), "tespit")
(PROJE / "testseti" / "yazim_etiket_listesi_k29.json").write_text(json.dumps(liste, ensure_ascii=False, indent=1),
                                                                  encoding="utf-8")
