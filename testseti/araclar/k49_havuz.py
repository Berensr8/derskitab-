"""K49 Bağımsız Değerlendirme 4: ön kayıtlı kilitli A sayfaları ve B havuzu seçimi.

Yeni kitaplarda (tarih9, cografya9) ölçümde kullanılacak sayfaları sabit bir tohumla (20261123),
sistem çalıştırılmadan önce seçer ve veri/bagimsiz4/havuz.json'a LF satır sonlarıyla yazar.
Seçim kuralı K42/K45 ile aynı (k45_havuz.py): ilk ve son 10 sayfa hariç, en az 150 kelime paragraf.
"""

import hashlib
import json
import random
import sys
from pathlib import Path

import pymupdf

PROJE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE))
sys.stdout.reconfigure(encoding="utf-8")

BEKLENEN_PYMUPDF = "1.28.2"
if pymupdf.__version__ != BEKLENEN_PYMUPDF:
    sys.exit(f"DUR: PyMuPDF {pymupdf.__version__}; beklenen {BEKLENEN_PYMUPDF}. .venv Python'u kullanın.")

TOHUM = 20261123
HAVUZ_YOLU = PROJE / "veri" / "bagimsiz4" / "havuz.json"
KITAPLAR = ["tarih9", "cografya9"]
A_SAYISI = 15


def havuz_olustur(tohum: int = TOHUM) -> dict:
    r = random.Random(tohum)
    a_secilen: dict[str, list[int]] = {}
    b_havuz: dict[str, list[int]] = {}
    for kitap in KITAPLAR:
        bl = json.loads((PROJE / "veri" / f"{kitap}_bloklar.json").read_text(encoding="utf-8"))
        with pymupdf.open(PROJE / "veri" / f"{kitap}.pdf") as doc:
            toplam_sayfa = len(doc)
        son = max(x["sayfa_no"] for x in bl)
        say: dict[int, int] = {}
        for x in bl:
            if x["tur"] == "paragraf":
                say[x["sayfa_no"]] = say.get(x["sayfa_no"], 0) + len(x["metin"].split())
        uygun = sorted(s for s, n in say.items() if n >= 150 and 10 < s < son - 10)
        a_secilen[kitap] = sorted(r.sample(uygun, A_SAYISI))
        a_haric = set(a_secilen[kitap])
        b_havuz[kitap] = [s for s in range(1, toplam_sayfa + 1) if s not in a_haric]
    return {"tohum": tohum, "A": a_secilen, "B_havuz": b_havuz}


def havuz_kaydet(veri: dict, yol: Path = HAVUZ_YOLU) -> tuple[Path, str]:
    yol.parent.mkdir(parents=True, exist_ok=True)
    ham = json.dumps(veri, ensure_ascii=False, indent=1).encode("utf-8")
    yol.write_bytes(ham)
    return yol, hashlib.sha256(ham).hexdigest()


if __name__ == "__main__":
    veri = havuz_olustur(TOHUM)
    yol, sha256 = havuz_kaydet(veri)
    print(f"Havuz kaydedildi: {yol}")
    print(f"SHA-256: {sha256}")
    for k in KITAPLAR:
        print(f"A ({k}, {len(veri['A'][k])} sayfa): {veri['A'][k]}")
        print(f"B havuz ({k}): {len(veri['B_havuz'][k])} sayfa (A dışındaki tüm sayfalar)")
