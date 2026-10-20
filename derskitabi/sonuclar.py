"""Bir kitabın üç kriterdeki sonuçlarını tek yerde toplar (notlu PDF ve Excel raporu aynı
tespitleri kullansın diye).

Verilmeyen sonuçlar burada hesaplanır (yazım, okunabilirlik — hızlı) ya da PDF'in yanındaki
dosyadan okunur (tutarlılık — yerel modeller gerekir, uzun sürer; dosya yoksa None =
"çalıştırılmadı").
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .inceleyici import tutarlilik_kaydi_yukle
from .kayit import bloklari_yukle, tespitleri_yukle
from .kriterler import okunabilirlik, yazim
from .model import Blok, Tespit
from .pdf_cikarma import bloklari_cikar


@dataclass
class KitapSonuclari:
    bloklar: list[Blok]
    tespitler: dict[str, list[Tespit] | None]  # {"yazim": …, "okunabilirlik": …, "tutarlilik": … ya da None}
    okunabilirlik_ozeti: "okunabilirlik.KitapOzeti | None" = None
    tutarlilik_kaydi: list[dict] | None = None


def sonuclari_topla(pdf_yolu, bloklar: list[Blok] | None = None, hedef_sinif: int | None = None,
                    yazim_tespitleri: list[Tespit] | None = None, okunabilirlik_analizi: tuple | None = None,
                    tutarlilik_tespitleri: list[Tespit] | None = None, tutarlilik_kaydi: list[dict] | None = None,
                    hakem: bool = False, ilerleme=None) -> KitapSonuclari:
    """okunabilirlik_analizi: okunabilirlik.analiz_et() çıktısı (özet, tespitler) önceden hesaplandıysa."""
    yaz = ilerleme or (lambda _m: None)
    pdf_yolu = Path(pdf_yolu)
    kok = pdf_yolu.with_suffix("")
    if bloklar is None:
        kayitli = Path(f"{kok}_bloklar.json")
        bloklar = bloklari_yukle(kayitli) if kayitli.exists() else bloklari_cikar(pdf_yolu)
    if okunabilirlik_analizi is None:
        try:
            okunabilirlik_analizi = okunabilirlik.analiz_et(bloklar, hedef_sinif)
        except ValueError:  # skorlanabilen paragraf yok
            okunabilirlik_analizi = (None, [])
    if yazim_tespitleri is None:
        yaz("Yazım denetimi…")
        yazim_tespitleri = yazim.analiz_et(bloklar)
        if hakem:
            from .kriterler.yazim_hakem import hakemle
            onbellek_yolu = pdf_yolu.with_name("yazim_hakem_onbellek.json")
            onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
            try:
                yazim_tespitleri = hakemle(yazim_tespitleri, bloklar, onbellek=onbellek, ilerleme=yaz)
            finally:
                onbellek_yolu.write_text(json.dumps(onbellek, ensure_ascii=False), encoding="utf-8")
    if tutarlilik_tespitleri is None:
        yol = Path(f"{kok}_tutarlilik_tespitler.json")
        tutarlilik_tespitleri = tespitleri_yukle(yol) if yol.exists() else None
    if tutarlilik_kaydi is None and tutarlilik_tespitleri:
        tutarlilik_kaydi = tutarlilik_kaydi_yukle(pdf_yolu)
    ozet, okunabilirlik_tespitleri = okunabilirlik_analizi
    return KitapSonuclari(bloklar, {"yazim": yazim_tespitleri, "okunabilirlik": okunabilirlik_tespitleri,
                                    "tutarlilik": tutarlilik_tespitleri}, ozet, tutarlilik_kaydi)
