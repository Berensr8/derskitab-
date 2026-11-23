"""K49 ölçümü için ortak yardımcılar: ortam kontrolü, kilitli havuz doğrulaması (k45_ortak.py düzeninde).

Ölçüm betikleri başta `ortam_kontrol()` çağırır; PyMuPDF sürümü, ölçülecek kod sürümü ve havuz parmak izi
ön kayıttakiyle (testseti/k49_on_kayit.md) aynı değilse durur.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pymupdf

PROJE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE))
sys.stdout.reconfigure(encoding="utf-8")

BEKLENEN_PYMUPDF = "1.28.2"
OLCULECEK_SURUM = "68a7a71"  # ölçülecek ürün kodu (K48 sonu)
TOHUM = 20261123
HAVUZ_YOLU = PROJE / "veri" / "bagimsiz4" / "havuz.json"
HAVUZ_SHA256 = "8b15506e0e960635fffd7285f56f0d63697e30983a1aa09f4eee6c3ec166bebd"  # k49_on_kayit.md
CIKTI = PROJE / "veri" / "bagimsiz4"
PAKET = PROJE / "bagimsiz_degerlendirme4"
KITAPLAR = ["tarih9", "cografya9"]
KITAP_AD = {"tarih9": "Tarih 9", "cografya9": "Coğrafya 9"}

B1_SAYISI = 80
B2_SAYISI = 60
KURAL_BASINA = 10
KURALLAR = [
    "bitisik_rakam",
    "yil_virgul_bosluk",
    "liste_tutarsiz_virgul",
    "iki_nokta_bosluk",
    "yonerge_cift_nokta",
    "yonerge_soru_isareti",
    "bir_takim",
    "birim_gr",
    "yanlis_kelime",
    "buyuk_harf_i",
    "kesme_bosluk",
]


def _git(*arg) -> str:
    return subprocess.run(["git", *arg], capture_output=True, text=True, encoding="utf-8", cwd=PROJE).stdout


def sha256_dosya_lf(yol: Path) -> str:
    """Satır sonları LF'ye çevrilmiş içeriğin SHA-256'sı (Windows CRLF yazabildiği için)."""
    return hashlib.sha256(yol.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def ortam_kontrol(sert: bool = True) -> dict:
    """sert=True: çalışma ağacı tamamen temiz olmalı. sert=False: yalnız ürün kodu (derskitabi/) değişmemiş olmalı."""
    if pymupdf.__version__ != BEKLENEN_PYMUPDF:
        sys.exit(f"DUR: PyMuPDF {pymupdf.__version__}; beklenen {BEKLENEN_PYMUPDF}. .venv Python'u kullanın.")
    if _git("diff", OLCULECEK_SURUM, "--stat", "--", "derskitabi").strip():
        sys.exit(f"DUR: derskitabi/ kodu ölçülecek sürümden ({OLCULECEK_SURUM}) farklı.")
    kirli = _git("status", "--porcelain", *([] if sert else ["--", "derskitabi"])).strip()
    if kirli:
        sys.exit("DUR: çalışma ağacı temiz değil:\n" + kirli)
    if sha256_dosya_lf(HAVUZ_YOLU) != HAVUZ_SHA256:
        sys.exit("DUR: havuz.json parmak izi ön kayıttakiyle uyuşmuyor.")
    return {"commit": _git("rev-parse", "HEAD").strip(), "pymupdf": pymupdf.__version__}


def havuz() -> dict:
    return json.loads(HAVUZ_YOLU.read_text(encoding="utf-8"))


def olcum_sayfalari(kitap: str) -> set[int]:
    """Bir kitabın A ve B havuzu sayfaları (bütün kitap)."""
    h = havuz()
    return set(h["A"].get(kitap, [])) | set(h["B_havuz"].get(kitap, []))
