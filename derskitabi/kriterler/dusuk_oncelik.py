"""Yazım tespitlerini düşük önceliğe indiren kitap ipuçları, tek yerden (K28, K29).

Sıra: önce PDF okuma parçası (kelime hiç kelime değil), sonra terim (kitap kendisi açıklıyor),
sonra alıntı (yazarın ya da eski yazım). Bir tespit yalnız ilk uyan sebeple işaretlenir;
hiçbiri silinmez. Yazım hakemi (K25) bu tespitleri modele sormaz.
"""

from ..model import Blok, Tespit
from . import alinti, pdf_parcasi, terim

# açıklamadaki not -> raporda gösterilen kısa ad
KITAP_IPUCU_NOTLARI = {pdf_parcasi.PARCA_NOTU: "PDF okuma parçası", terim.TERIM_NOTU + ":": "terim",
                       alinti.ALINTI_NOTU: "alıntı içinde"}
YALNIZ_BIR_ARAC_NOTU = "yalnız bir araç tanımadı"
NOTLAR = {**KITAP_IPUCU_NOTLARI, YALNIZ_BIR_ARAC_NOTU: "yalnız bir araç tanımadı"}


def sebep(t: Tespit) -> str | None:
    """Tespit bir kitap ipucuyla veya tek araç kararsızlığıyla düşük önceliğe indiyse kısa adı."""
    return next((ad for not_, ad in NOTLAR.items() if not_ in t.aciklama), None)


def _yalniz_isaretsizlere(islem, tespitler: list[Tespit]) -> list[Tespit]:
    """İşlemi henüz kitap ipucuyla işaretlenmemiş tespitlere uygular; sıra korunur."""
    sira = [i for i, t in enumerate(tespitler) if not any(not_ in t.aciklama for not_ in KITAP_IPUCU_NOTLARI)]
    sonuc = list(tespitler)
    for i, t in zip(sira, islem([tespitler[i] for i in sira])):
        sonuc[i] = t
    return sonuc


def isaretle(pdf_yolu, bloklar: list[Blok], tespitler: list[Tespit], denetciler=None) -> list[Tespit]:
    """PDF okuma parçası, terim ve alıntı ipuçlarını uygular (yazı biçimleri PDF'ten okunur)."""
    tespitler = pdf_parcasi.isaretle(tespitler, bloklar, denetciler)
    sayfalar = {t.sayfa_no for t in tespitler if t.alt_tur == "morfoloji" and not any(not_ in t.aciklama for not_ in KITAP_IPUCU_NOTLARI)}
    italikler = terim.italik_kelimeler(pdf_yolu, bloklar, sayfalar) if pdf_yolu else None
    tespitler = _yalniz_isaretsizlere(lambda ts: terim.isaretle(ts, bloklar, italikler, denetciler), tespitler)
    if pdf_yolu:
        tespitler = _yalniz_isaretsizlere(lambda ts: alinti.pdf_ile_isaretle(pdf_yolu, bloklar, ts), tespitler)
    return tespitler
