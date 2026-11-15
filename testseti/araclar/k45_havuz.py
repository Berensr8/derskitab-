"""K45 Bağımsız Değerlendirme 3: Ön kayıtlı kilitli A sayfaları ve B havuzu seçimi.

Yeni kitaplarda (biyoloji12, inkilap12) ölçüm zamanı kullanılacak sayfaları
sabit bir tohumla (20261116) seçer ve veri/bagimsiz3/havuz.json'a LF satır sonlarıyla yazar.
"""

import hashlib
import json
from pathlib import Path
import random
import sys

import pymupdf

PROJE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE))

BEKLENEN_PYMUPDF = "1.28.2"
if pymupdf.__version__ != BEKLENEN_PYMUPDF:
    sys.exit(f"DUR: PyMuPDF {pymupdf.__version__}; beklenen {BEKLENEN_PYMUPDF}. .venv Python'u kullanın.")

TOHUM = 20261116
HAVUZ_YOLU = PROJE / "veri" / "bagimsiz3" / "havuz.json"
KITAPLAR = ["biyoloji12", "inkilap12"]


def havuz_olustur(tohum: int = TOHUM) -> dict:
    r = random.Random(tohum)

    # 1. A sayfaları: her kitaptan 15 sayfa (ilk ve son 10 sayfa hariç, >=150 kelime paragraf)
    a_secilen: dict[str, list[int]] = {}
    b_havuz: dict[str, list[int]] = {}
    for kitap in KITAPLAR:
        bl = json.loads((PROJE / "veri" / f"{kitap}_bloklar.json").read_text(encoding="utf-8"))
        with pymupdf.open(PROJE / "veri" / f"{kitap}.pdf") as doc:
            toplam_sayfa = len(doc)
        son = max(x["sayfa_no"] for x in bl)
        say = {}
        for x in bl:
            if x["tur"] == "paragraf":
                say[x["sayfa_no"]] = say.get(x["sayfa_no"], 0) + len(x["metin"].split())
        uygun = sorted(s for s, n in say.items() if n >= 150 and 10 < s < son - 10)
        a_secilen[kitap] = sorted(r.sample(uygun, 15))

        # 2. B havuzu: kitabın A dışındaki bütün sayfaları
        a_haric = set(a_secilen[kitap])
        b_havuz[kitap] = [s for s in range(1, toplam_sayfa + 1) if s not in a_haric]

    return {
        "tohum": tohum,
        "A": a_secilen,
        "B_havuz": b_havuz,
    }


def havuz_kaydet(veri: dict, yol: Path = HAVUZ_YOLU) -> tuple[Path, str]:
    yol.parent.mkdir(parents=True, exist_ok=True)
    icerik = json.dumps(veri, ensure_ascii=False, indent=1)
    ham = icerik.encode("utf-8")
    yol.write_bytes(ham)
    sha256 = hashlib.sha256(ham).hexdigest()
    return yol, sha256


if __name__ == "__main__":
    veri = havuz_olustur(TOHUM)
    yol, sha256 = havuz_kaydet(veri)
    print(f"Havuz kaydedildi: {yol}")
    print(f"SHA-256: {sha256}")
    for k in KITAPLAR:
        print(f"A ({k}, {len(veri['A'][k])} sayfa): {veri['A'][k]}")
        print(f"B havuz ({k}): {len(veri['B_havuz'][k])} sayfa (A dışındaki tüm sayfalar)")
