"""Kavramsal yük işaretleri (K30): okunabilirlik formüllerinin ölçmediği kelime tanıdıklığı ve terim.

Formüller yalnız cümle ve kelime uzunluğunu ölçer (K24: sınıf düzeyini ayırt etmiyor). Burada
paragrafın kelimelerine bakılır (≥4 harfli kelimeler):
  - nadir_oran     : ne kendisi ne kökü genel Türkçe sıklık listesinin ilk 10.000 kelimesinde
                     olan kelimelerin oranı (tr_50k: OpenSubtitles 2018, hermitdave/FrequencyWords)
  - ort_log_sira   : kelimelerin sıklık sırasının logaritmasının ortalaması (listede yoksa 50.001)
  - terim_orani    : iki morfoloji aracının da tanımadığı kelimelerin oranı
"""

import functools
import math
from dataclasses import dataclass
from pathlib import Path

from . import yazim

SIKLIK_YOLU = Path(__file__).resolve().parents[2] / "kaynaklar" / "tr_50k.txt"
TANIDIK_SINIRI = 10_000
LISTEDE_YOK = 50_001
EN_KISA = 4


@functools.cache
def siklik_sirasi() -> dict[str, int]:
    """{kelime: sıra} (1 = en sık)."""
    sira = {}
    for i, satir in enumerate(SIKLIK_YOLU.read_text(encoding="utf-8").splitlines(), start=1):
        kelime = satir.split(" ")[0]
        sira.setdefault(yazim.tr_kucuk(kelime), i)
    return sira


@functools.cache
def _kok(kelime: str) -> str | None:
    try:
        c = yazim.starlang_cozumleyici().morphologicalAnalysis(kelime)
        return yazim.tr_kucuk(c.getFsmParse(0).getWord().getName()) if c.size() else None
    except (ValueError, IndexError, KeyError):
        return None


def kelime_sirasi(kelime: str) -> int:
    """Kelimenin ya da kökünün sıklık sırası (hangisi daha sıksa)."""
    sira = siklik_sirasi()
    k = yazim.tr_kucuk(kelime)
    kok = _kok(k)
    return min(sira.get(k, LISTEDE_YOK), sira.get(kok, LISTEDE_YOK) if kok else LISTEDE_YOK)


@dataclass
class KavramsalSkor:
    kelime_sayisi: int
    nadir_oran: float
    ort_log_sira: float
    terim_orani: float


def skorla(metin: str, denetciler=None) -> KavramsalSkor | None:
    denetciler = denetciler or yazim.varsayilan_denetciler()
    kelimeler = [k for k in yazim._KELIME.findall(metin) if len(k) >= EN_KISA and k[:1].islower()]
    if not kelimeler:
        return None
    siralar = [kelime_sirasi(k) for k in kelimeler]
    terim = [k for k in kelimeler if not any(yazim._gecerli(d, k) for d in denetciler)]
    return KavramsalSkor(len(kelimeler),
                         round(sum(s > TANIDIK_SINIRI for s in siralar) / len(kelimeler), 4),
                         round(sum(math.log(s) for s in siralar) / len(kelimeler), 4),
                         round(len(terim) / len(kelimeler), 4))
