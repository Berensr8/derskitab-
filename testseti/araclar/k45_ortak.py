"""K45 ölçümü için ortak yardımcılar: ortam kontrolü, kilitli havuz doğrulaması.

Ölçüm betikleri başta `ortam_kontrol()` çağırır; PyMuPDF sürümü, ölçülecek kod sürümü ve
havuz parmak izi ön kayıttakiyle (testseti/k45_on_kayit.md) aynı değilse durur.
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
OLCULECEK_SURUM = "ba44473"  # ölçülecek ürün kodu (K44 sonu)
TOHUM = 20261116
HAVUZ_YOLU = PROJE / "veri" / "bagimsiz3" / "havuz.json"
HAVUZ_SHA256 = "db127255975e612b46d628368a944f850b79b300f043367459cd2a8908f68702"  # k45_on_kayit.md
CIKTI = PROJE / "veri" / "bagimsiz3"
PAKET = PROJE / "bagimsiz_degerlendirme3"
KITAPLAR = ["biyoloji12", "inkilap12"]
KITAP_AD = {"biyoloji12": "Biyoloji 12", "inkilap12": "İnkılâp 12"}
KITAP_TAM_AD = {"biyoloji12": "Biyoloji 12", "inkilap12": "T.C. İnkılâp Tarihi ve Atatürkçülük 12"}

K44_KURALLAR = [
    "bitisik_rakam",
    "yil_virgul_bosluk",
    "liste_tutarsiz_virgul",
    "iki_nokta_bosluk",
    "yonerge_cift_nokta",
    "yonerge_soru_isareti",
    "bir_takim",
    "birim_gr",
    "yanlis_kelime",
]
YENI_KURALLAR = K44_KURALLAR + ["buyuk_harf_i"]


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
