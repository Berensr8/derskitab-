"""Uzun yerel model işlerinde bilgisayarı korumak: güç kaynağı ve ekran kartı sıcaklığı.

2026-10-20'de saatler süren tam yük çalışmada önce NVIDIA sürücüsü sıfırlandı (ekran gitti),
sonra güç kaynağı pile geçince dizüstü bilgisayar aniden kapandı. Bekçi her birkaç istekte bir
kontrol eder:
  - bilgisayar pildeyse iş duraklar, şarja takılınca kendiliğinden devam eder;
  - ekran kartı SICAKLIK_UST'ü geçerse SICAKLIK_DEVAM'a inene kadar bekler;
  - her DINLENME_ARALIGI istekte bir kısa mola verir.
Kontrol yapılamazsa (Windows dışı, nvidia-smi yok) iş durdurulmaz.
"""

import ctypes
import subprocess
import sys
import time
from collections.abc import Callable

KONTROL_ARALIGI = 20  # istek
DINLENME_ARALIGI = 150  # istek
DINLENME_SN = 15
SICAKLIK_UST = 83  # °C
SICAKLIK_DEVAM = 72  # °C
BEKLEME_SN = 30


class _GucDurumu(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]


def prizde_mi() -> bool | None:
    """True: prizde, False: pilde, None: bilinmiyor."""
    if sys.platform != "win32":
        return None
    durum = _GucDurumu()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(durum)):
        return None
    return {0: False, 1: True}.get(durum.ACLineStatus)


def gpu_sicakligi() -> int | None:
    try:
        cikti = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=10).stdout
        return int(cikti.split()[0])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


class Bekci:
    """Her istekten önce adim() çağrılır; gerekirse bekletir."""

    def __init__(self, yaz: Callable[[str], None] = print, uyku: Callable[[float], None] = time.sleep,
                 prizde=prizde_mi, sicaklik=gpu_sicakligi):
        self.n, self.yaz, self.uyku, self.prizde, self.sicaklik = 0, yaz, uyku, prizde, sicaklik

    def adim(self) -> None:
        self.n += 1
        if self.n % DINLENME_ARALIGI == 0:
            self.uyku(DINLENME_SN)
        if self.n % KONTROL_ARALIGI:
            return
        if self.prizde() is False:
            self.yaz("  ⚠ Bilgisayar pilde: ağır iş duraklatıldı, şarja takınca devam edecek.")
            while self.prizde() is False:
                self.uyku(BEKLEME_SN)
            self.yaz("  Prize takıldı, devam ediliyor.")
        t = self.sicaklik()
        if t is not None and t >= SICAKLIK_UST:
            self.yaz(f"  ⚠ Ekran kartı {t}°C: {SICAKLIK_DEVAM}°C'ye inene kadar bekleniyor.")
            while (t := self.sicaklik()) is not None and t > SICAKLIK_DEVAM:
                self.uyku(BEKLEME_SN)
            self.yaz("  Soğudu, devam ediliyor.")
