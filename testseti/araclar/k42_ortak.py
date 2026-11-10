"""K42 ölçümü için ortak yardımcılar: ortam kontrolü, kilitli havuz doğrulaması.

Ölçüm betikleri başta `ortam_kontrol()` çağırır; PyMuPDF sürümü, ölçülecek kod sürümü ve
havuz parmak izi ön kayıttakiyle (testseti/k42_on_kayit.md) aynı değilse durur.
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
OLCULECEK_SURUM = "854559a"  # ölçülecek ürün kodu (K41-ek4)
HAVUZ_YOLU = PROJE / "veri" / "bagimsiz2" / "havuz.json"
HAVUZ_SHA256 = "1e96023b2b015f9c87eca7f4a26e431a610fef9afe0dc5bdbe6e86c0cfc36c27"  # on_kayit.md
CIKTI = PROJE / "veri" / "bagimsiz2"
PAKET = PROJE / "bagimsiz_degerlendirme2"
KITAPLAR = ["biyoloji9", "biyoloji11", "turkdili10", "turkdili11", "turkdili12"]
KITAP_AD = {"biyoloji9": "Biyoloji 9", "biyoloji11": "Biyoloji 11", "turkdili10": "TDE 10",
            "turkdili11": "TDE 11", "turkdili12": "TDE 12"}
# K41'de eklenen yeni yazım kuralları (alt_tur adları)
YENI_KURALLAR = ["buyuk_harf_i", "dizgi_rakam_harf", "duzeltme_isareti_nispet",
                 "noktalama_cift_tek_tirnak", "noktalama_parantez_cift_nokta", "noktalama_ters_tirnak"]


def _git(*arg) -> str:
    return subprocess.run(["git", *arg], capture_output=True, text=True, encoding="utf-8", cwd=PROJE).stdout


def sha256_dosya_lf(yol: Path) -> str:
    """Satır sonları LF'ye çevrilmiş içeriğin SHA-256'sı (Windows CRLF yazdığı için)."""
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
    icerik = json.dumps(json.loads(HAVUZ_YOLU.read_text(encoding="utf-8")), ensure_ascii=False, indent=1)
    if hashlib.sha256(icerik.encode("utf-8")).hexdigest() != HAVUZ_SHA256:
        sys.exit("DUR: havuz.json içeriğinin (json.dumps) parmak izi uyuşmuyor.")
    return {"commit": _git("rev-parse", "HEAD").strip(), "pymupdf": pymupdf.__version__}


def havuz() -> dict:
    return json.loads(HAVUZ_YOLU.read_text(encoding="utf-8"))


def olcum_sayfalari(kitap: str) -> set[int]:
    """Bir kitabın A ve B havuzu sayfaları."""
    h = havuz()
    return set(h["A"].get(kitap, [])) | set(h["B_havuz"].get(kitap, []))
