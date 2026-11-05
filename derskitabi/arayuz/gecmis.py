"""İnceleme geçmişi: her inceleme için bir kayıt (incelemeler/gecmis/<id>.json).

Kayıtta kullanıcı alanı şimdiden var ("yerel"); üye girişi eklenince listeler kullanıcıya göre süzülür.
Asıl sonuç dosyaları kullanıcının seçtiği çıktı klasöründe durur; kayıt yalnız oraya işaret eder.
"""

import json
import re
import time
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
GECMIS = PROJE / "incelemeler" / "gecmis"
VARSAYILAN_CIKTI = PROJE / "incelemeler"
KULLANICI = "yerel"


def _yol(kimlik: str) -> Path:
    if not re.fullmatch(r"[\w-]+", kimlik):
        raise ValueError(f"Geçersiz inceleme kimliği: {kimlik!r}")
    return GECMIS / f"{kimlik}.json"


def yeni(ayar: dict) -> dict:
    GECMIS.mkdir(parents=True, exist_ok=True)
    kimlik = time.strftime("%Y%m%d-%H%M%S")
    while _yol(kimlik).exists():
        kimlik += "b"
    kayit = {"id": kimlik, "kullanici": KULLANICI, "kitap_adi": ayar.get("kitap_adi") or Path(ayar["pdf"]).stem,
             "pdf": ayar["pdf"], "cikti": ayar["cikti"], "ayar": ayar, "baslangic": time.time(), "bitis": None,
             "durum": "sürüyor", "pid": None, "ozet_sayilari": None}
    kaydet(kayit)
    return kayit


def kaydet(kayit: dict) -> None:
    GECMIS.mkdir(parents=True, exist_ok=True)
    gecici = _yol(kayit["id"]).with_suffix(".tmp")
    gecici.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    gecici.replace(_yol(kayit["id"]))


def oku(kimlik: str) -> dict | None:
    yol = _yol(kimlik)
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else None


def listele(kullanici: str = KULLANICI) -> list[dict]:
    if not GECMIS.exists():
        return []
    kayitlar = []
    for yol in GECMIS.glob("*.json"):
        try:
            k = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if k.get("kullanici", KULLANICI) == kullanici:
            kayitlar.append(k)
    return sorted(kayitlar, key=lambda k: -k["baslangic"])


def sil(kimlik: str) -> None:
    """Yalnız geçmiş kaydını siler; çıktı klasörüne dokunmaz."""
    _yol(kimlik).unlink(missing_ok=True)
