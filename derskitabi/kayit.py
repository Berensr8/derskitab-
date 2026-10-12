"""Blok ve tespit listelerini JSON dosyasına yazma / okuma.

Dosya formatıyla ilgili her şey bu modülde toplanır (K3). İleride SQLite'a
geçilirse yalnızca bu dosya değişir.
"""

import json
from pathlib import Path

from .model import Blok, Tespit


def _yaz(nesneler, yol) -> None:
    veri = [n.sozluge() for n in nesneler]
    Path(yol).write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")


def _oku(yol) -> list[dict]:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def json_kaydet(veri: dict, yol) -> None:
    """Kitap özeti gibi tek bir sözlüğü kaydeder."""
    Path(yol).write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")


def bloklari_kaydet(bloklar: list[Blok], yol) -> None:
    _yaz(bloklar, yol)


def bloklari_yukle(yol) -> list[Blok]:
    return [Blok.sozlukten(d) for d in _oku(yol)]


def tespitleri_kaydet(tespitler: list[Tespit], yol) -> None:
    _yaz(tespitler, yol)


def tespitleri_yukle(yol) -> list[Tespit]:
    return [Tespit.sozlukten(d) for d in _oku(yol)]
