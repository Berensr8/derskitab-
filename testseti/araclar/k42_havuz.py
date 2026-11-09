"""K42 Bağımsız Değerlendirme 2: Ön kayıtlı kilitli A sayfaları ve B havuzu seçimi (K40).

Ölçüm zamanı kullanılacak sayfaları sabit bir tohumla seçer ve veri/bagimsiz2/havuz.json'a yazar.
Geliştirme sırasında bu sayfalara ve bu sayfalardaki çıktılara bakılmaz.
"""

import hashlib
import json
from pathlib import Path
import random
import sys

PROJE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE))

from derskitabi.yazim_modeli.veri import test_sayfalari

TOHUM = 20261110
HAVUZ_YOLU = PROJE / "veri" / "bagimsiz2" / "havuz.json"
A_KITAPLAR = ["biyoloji9", "biyoloji11", "turkdili10"]
B_KITAPLAR = ["biyoloji9", "biyoloji11", "turkdili10", "turkdili11", "turkdili12"]


def k39_sayfalari() -> dict[str, set[int]]:
    """K39 bağımsız değerlendirmesinde kullanılan A ve B sayfaları."""
    haric = {}
    a_yol = PROJE / "testseti" / "bagimsiz" / "A_sayfa_listesi.json"
    if a_yol.exists():
        for x in json.loads(a_yol.read_text(encoding="utf-8")):
            haric.setdefault(x["kitap"], set()).add(x["sayfa_no"])
    b_yol = PROJE / "testseti" / "bagimsiz" / "B_anahtar.json"
    if b_yol.exists():
        for x in json.loads(b_yol.read_text(encoding="utf-8")):
            haric.setdefault(x["kitap"], set()).add(x["sayfa_no"])
    return haric


def havuz_olustur(tohum: int = TOHUM) -> dict:
    r = random.Random(tohum)
    test_sf = test_sayfalari()
    k39_sf = k39_sayfalari()

    yasak = {}
    for k, v in test_sf.items():
        yasak.setdefault(k, set()).update(v)
    for k, v in k39_sf.items():
        yasak.setdefault(k, set()).update(v)

    # 1. A sayfaları: Biyoloji 9, Biyoloji 11, TDE 10'dan 10'ar sayfa (>=150 kelime paragraf)
    a_secilen: dict[str, list[int]] = {}
    for kitap in A_KITAPLAR:
        bl = json.loads((PROJE / "veri" / f"{kitap}_bloklar.json").read_text(encoding="utf-8"))
        son = max(x["sayfa_no"] for x in bl)
        say = {}
        for x in bl:
            if x["tur"] == "paragraf":
                say[x["sayfa_no"]] = say.get(x["sayfa_no"], 0) + len(x["metin"].split())
        uygun = sorted(s for s, n in say.items()
                       if n >= 150 and s not in yasak.get(kitap, set()) and 10 < s < son - 10)
        a_secilen[kitap] = sorted(r.sample(uygun, 10))

    # 2. B havuzu: 5 kitaptan 40'ar sayfa (A sayfalarıyla çakışmaz)
    b_havuz: dict[str, list[int]] = {}
    for kitap in B_KITAPLAR:
        bl = json.loads((PROJE / "veri" / f"{kitap}_bloklar.json").read_text(encoding="utf-8"))
        son = max(x["sayfa_no"] for x in bl)
        a_haric = set(a_secilen.get(kitap, []))
        uygun = sorted(s for s in range(11, son - 10)
                       if s not in yasak.get(kitap, set()) and s not in a_haric)
        b_havuz[kitap] = sorted(r.sample(uygun, 40))

    veri = {
        "tohum": tohum,
        "A": a_secilen,
        "B_havuz": b_havuz,
    }
    return veri


def havuz_kaydet(veri: dict, yol: Path = HAVUZ_YOLU) -> tuple[Path, str]:
    yol.parent.mkdir(parents=True, exist_ok=True)
    icerik = json.dumps(veri, ensure_ascii=False, indent=1)
    yol.write_text(icerik, encoding="utf-8")
    sha256 = hashlib.sha256(icerik.encode("utf-8")).hexdigest()
    return yol, sha256


def haric_sayfalar(havuz_yolu: Path = HAVUZ_YOLU) -> dict[str, set[int]]:
    """Geliştirme betiklerinin atlaması gereken kilitli ölçüm sayfaları (A + B havuzu)."""
    if not havuz_yolu.exists():
        veri = havuz_olustur()
    else:
        veri = json.loads(havuz_yolu.read_text(encoding="utf-8"))
    haric = {}
    for k, sayfalar in veri.get("A", {}).items():
        haric.setdefault(k, set()).update(sayfalar)
    for k, sayfalar in veri.get("B_havuz", {}).items():
        haric.setdefault(k, set()).update(sayfalar)
    return haric


if __name__ == "__main__":
    veri = havuz_olustur(TOHUM)
    yol, sha256 = havuz_kaydet(veri)
    print(f"Havuz kaydedildi: {yol}")
    print(f"SHA-256: {sha256}")
    print("A sayfa sayıları:", {k: len(v) for k, v in veri["A"].items()})
    print("B havuz sayfa sayıları:", {k: len(v) for k, v in veri["B_havuz"].items()})
