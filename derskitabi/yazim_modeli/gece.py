"""Gece betiği (K33): Vikipedi çiftleri → veri → eğitim → ölçüm, sırayla ve kendiliğinden.

  - Her adım ayrı süreçte çalışır (Windows'ta pyarrow ile torch aynı süreçte DLL çakışması yapıyor).
  - Biten adım tekrar çalıştırılmaz: betik yarıda kalırsa yeniden başlatılınca kaldığı yerden sürer
    (eğitim de kendi kayıt noktasından devam eder).
  - Vikipedi adımları başarısız olursa eğitim Vikipedi verisi olmadan yapılır; gece boşa gitmez.
  - Çalıştığı sürece Windows'tan bilgisayarı uyutmamasını ister (SetThreadExecutionState). Sistem ayarı
    değişmez; betik bitince istek kendiliğinden kalkar. Kapak kapatılırsa uyku yine olabilir.

Kullanım:
    python -m derskitabi.yazim_modeli.gece [--fark-saat 2.5] [--egitim-saat 7]
"""

import argparse
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
VIKI = PROJE / "veri" / "vikipedi"
VERI = PROJE / "veri" / "yazim_modeli"
GUNLUK = VERI / "gece.log"
DOKUM = VIKI / "trwiki-latest-stub-meta-history.xml.gz"
PY = sys.executable


def yaz(m: str) -> None:
    satir = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {m}"
    print(satir, flush=True)
    with open(GUNLUK, "a", encoding="utf-8") as g:
        g.write(satir + "\n")


def uyanik_tut(acik: bool) -> None:
    if sys.platform == "win32":
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if acik else 0))


def adim(ad: str, *arg: str, gunluk: Path) -> bool:
    yaz(f"▶ {ad}")
    with open(gunluk, "a", encoding="utf-8") as g:
        sonuc = subprocess.run([PY, "-u", "-m", *arg], cwd=PROJE, stdout=g, stderr=subprocess.STDOUT)
    yaz(f"{'✓' if sonuc.returncode == 0 else '✗'} {ad} (çıkış kodu {sonuc.returncode})")
    return sonuc.returncode == 0


def bekle_kilit() -> None:
    """Başka bir Vikipedi indiricisi çalışıyorsa bitmesini bekler (aynı dosyaya iki süreç yazmasın)."""
    kilit = VIKI / "fark.kilit"
    while kilit.exists():
        pid = kilit.read_text().strip()
        cikti = subprocess.run(["tasklist", "/fi", f"PID eq {pid}"], capture_output=True, text=True).stdout
        if pid not in cikti:
            kilit.unlink(missing_ok=True)  # süreç ölmüş, kilit artık geçersiz
            break
        yaz(f"Vikipedi indiricisi (süreç {pid}) hâlâ çalışıyor: bekleniyor.")
        time.sleep(300)


def bitti_mi(gunluk: Path, isaret: str) -> bool:
    return gunluk.exists() and isaret in gunluk.read_text(encoding="utf-8", errors="ignore")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="K33 gece betiği")
    ap.add_argument("--fark-saat", type=float, default=2.0, help="Eğitimden önce ek Vikipedi indirme süresi")
    ap.add_argument("--fark-en-fazla", type=int, default=30000)
    ap.add_argument("--egitim-saat", type=float, default=7.0)
    arg = ap.parse_args()
    VERI.mkdir(parents=True, exist_ok=True)
    uyanik_tut(True)
    try:
        yaz("Gece betiği başladı.")
        # 1–3 Vikipedi (başarısız olursa geçilir)
        viki_gunluk = VIKI / "gece_vikipedi.log"
        if not bitti_mi(VIKI / "aday.log", "Aday:"):
            adim("Vikipedi: aday değişiklikler", "derskitabi.yazim_modeli.vikipedi", "aday", str(DOKUM),
                 gunluk=VIKI / "aday.log")
        bekle_kilit()
        farklar = VIKI / "farklar.jsonl"
        yapilan = sum(1 for _ in open(farklar, encoding="utf-8")) if farklar.exists() else 0
        egitim_basladi = (VERI / "egitim.log").exists()  # eğitim başladıysa veri artık değişmez
        if (bitti_mi(VIKI / "aday.log", "Aday:") and yapilan < arg.fark_en_fazla and arg.fark_saat > 0
                and not egitim_basladi):
            adim(f"Vikipedi: farklar (API, {yapilan} hazır)", "derskitabi.yazim_modeli.vikipedi", "fark",
                 "--en-fazla", str(arg.fark_en_fazla), "--saat", str(arg.fark_saat), gunluk=viki_gunluk)
        if farklar.exists() and not egitim_basladi:
            adim("Vikipedi: çiftler", "derskitabi.yazim_modeli.vikipedi", "cift", gunluk=viki_gunluk)
        # 4 Veri
        veri_gunluk = VERI / "veri.log"
        if not bitti_mi(veri_gunluk, "Veri: {") or (VIKI / "ciftler.jsonl").exists() and \
                (VERI / "egitim.jsonl").exists() and \
                (VIKI / "ciftler.jsonl").stat().st_mtime > (VERI / "egitim.jsonl").stat().st_mtime:
            if not adim("Veri kurulumu", "derskitabi.yazim_modeli.veri", gunluk=veri_gunluk):
                yaz("Veri kurulamadı: durduruluyor.")
                return
        # 5 Eğitim
        egitim_gunluk = VERI / "egitim_cikti.log"
        if not bitti_mi(VERI / "egitim.log", "Eğitim bitti") and not bitti_mi(VERI / "egitim.log", "Erken durdurma"):
            for deneme in range(3):  # beklenmedik çökmede kayıttan iki kez daha dener
                if adim(f"Eğitim (deneme {deneme + 1})", "derskitabi.yazim_modeli.egit", "--saat",
                        str(arg.egitim_saat), gunluk=egitim_gunluk):
                    break
                time.sleep(60)
        # 6 Ölçüm
        if (PROJE / "modeller" / "yazim_modeli" / "en_iyi").exists():
            adim("Ölçüm", "derskitabi.yazim_modeli.olc", gunluk=VERI / "olcum.log")
            if (VERI / "olcum.json").exists():
                yaz("Sonuç: " + json.dumps(json.loads((VERI / "olcum.json").read_text(encoding="utf-8")),
                                          ensure_ascii=False)[:2000])
        else:
            yaz("En iyi model yok: ölçüm yapılmadı.")
        yaz("Gece betiği bitti.")
    finally:
        uyanik_tut(False)


if __name__ == "__main__":
    main()
