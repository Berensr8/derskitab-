"""Yazım tespitlerini düşük önceliğe indiren kitap ipuçları, tek yerden (K28, K29, K44).

Sıra: önce PDF okuma parçası (kelime hiç kelime değil), sonra terim (kitap kendisi açıklıyor),
sonra alıntı (yazarın ya da eski yazım), en son eski metin sayfası (sayfada sözlük dışı en az
4 farklı kelime kalmışsa). Bir tespit yalnız ilk uyan sebeple işaretlenir; hiçbiri silinmez.
Yazım hakemi (K25) bu tespitleri modele sormaz.
"""

from collections import defaultdict
from dataclasses import replace

from ..model import Blok, Tespit
from . import alinti, pdf_parcasi, terim, yazim

DUSUK_GUVEN = 0.25
ESKI_METIN_NOTU = "Eski metin sayfası"
ESKI_METIN_ESIGI = 4

# açıklamadaki not -> raporda gösterilen kısa ad
KITAP_IPUCU_NOTLARI = {pdf_parcasi.PARCA_NOTU: "PDF okuma parçası", terim.TERIM_NOTU + ":": "terim",
                       alinti.ALINTI_NOTU: "alıntı içinde", ESKI_METIN_NOTU: "eski metin sayfası"}
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


def eski_metin_sayfasi(tespitler: list[Tespit], bloklar: list[Blok], denetciler=None) -> list[Tespit]:
    """Kalan 'iki araç da tanımadı' morfoloji tespiti en az ESKI_METIN_ESIGI farklı kelime olan sayfalarda
    morfoloji ve kesme tespitlerini düşük önceliğe indirir (K44). Kitapta geçen geçerli bir kelimeye
    tek harf/hece uzaklıktaki gerçek yazım hataları (ör. Biyoloji 9 s.114 'molekullerinin') istisnadır."""
    adaylar = [t for t in tespitler if t.alt_tur == "morfoloji" and t.metin_parcasi
               and "iki araç da" in t.aciklama and not any(not_ in t.aciklama for not_ in KITAP_IPUCU_NOTLARI)]
    if not adaylar:
        return tespitler
    from .yazim_hakem import yakin_dogru_kelime
    denetciler = denetciler or yazim.varsayilan_denetciler()
    kitap_kelimeleri = yazim.kitap_kelime_sayilari(bloklar)
    yakinlar = {yazim.tr_kucuk(k) for k in {t.metin_parcasi for t in tespitler if t.alt_tur == "morfoloji" and t.metin_parcasi}
                if yakin_dogru_kelime(k, kitap_kelimeleri, denetciler)}
    sayfa_kelimeleri = defaultdict(set)
    for t in adaylar:
        k = yazim.tr_kucuk(t.metin_parcasi)
        if k not in yakinlar:
            sayfa_kelimeleri[t.sayfa_no].add(k)
    eski_sayfalar = {s for s, kelimeler in sayfa_kelimeleri.items() if len(kelimeler) >= ESKI_METIN_ESIGI}
    if not eski_sayfalar:
        return tespitler
    # Aynı sayfada ve aynı sütunda 'Günümüz Türkçesiyle' başlığından aşağıda kalan bloklar
    # günümüz Türkçesidir (ör. TDE 12 s.247); yan sütundaki 'Günümüz Türkçesiyle' (TDE 11 s.156)
    # sol sütundaki eski metin bloklarını etkilemez.
    gunumuz_kutulari = defaultdict(list)
    for b in bloklar:
        if b.sayfa_no in eski_sayfalar and yazim.tr_kucuk(b.metin.strip()) == "günümüz türkçesiyle":
            gunumuz_kutulari[b.sayfa_no].append(b.bbox)
    sonuc = []
    for t in tespitler:
        gunumuz_altinda = any(
            t.bbox[1] >= g_bbox[1] and abs(t.bbox[0] - g_bbox[0]) < 80
            for g_bbox in gunumuz_kutulari.get(t.sayfa_no, ())
        )
        if t.sayfa_no not in eski_sayfalar or any(not_ in t.aciklama for not_ in KITAP_IPUCU_NOTLARI) or gunumuz_altinda:
            sonuc.append(t)
        elif t.alt_tur == "morfoloji":
            if t.metin_parcasi and yazim.tr_kucuk(t.metin_parcasi) in yakinlar:
                sonuc.append(t)
            else:
                sonuc.append(replace(t, guven_skoru=min(t.guven_skoru, DUSUK_GUVEN),
                                     aciklama=f"{t.aciklama} {ESKI_METIN_NOTU}: sayfada sözlükte bulunmayan çok sayıda "
                                              f"kelime var (eski Türkçe ya da ağız özelliği olabilir) — düşük öncelik."))
        elif t.alt_tur in alinti.KESME_TURLERI:
            yeni_aciklama = t.aciklama.replace(" (TDK)", "").replace("(TDK)", "").strip()
            sonuc.append(replace(t, guven_skoru=min(t.guven_skoru, DUSUK_GUVEN),
                                 aciklama=f"{yeni_aciklama} {ESKI_METIN_NOTU}: eski metin aktarımı olabilir; "
                                          f"dipnot var mı kontrol edin (MEB TYMM 2.4.1) — düşük öncelik."))
        else:
            sonuc.append(t)
    return sonuc


def isaretle(pdf_yolu, bloklar: list[Blok], tespitler: list[Tespit], denetciler=None) -> list[Tespit]:
    """PDF okuma parçası, terim, alıntı ve eski metin sayfası ipuçlarını uygular (yazı biçimleri PDF'ten okunur)."""
    tespitler = pdf_parcasi.isaretle(tespitler, bloklar, denetciler)
    if pdf_yolu:  # K50: büyük harfli kelimede basılı harf noktalı İ ise metin katmanı farkıdır
        tespitler = pdf_parcasi.basili_i_isaretle(pdf_yolu, tespitler)
    sayfalar ={t.sayfa_no for t in tespitler if t.alt_tur == "morfoloji" and not any(not_ in t.aciklama for not_ in KITAP_IPUCU_NOTLARI)}
    italikler = terim.italik_kelimeler(pdf_yolu, bloklar, sayfalar) if pdf_yolu else None
    tespitler = _yalniz_isaretsizlere(lambda ts: terim.isaretle(ts, bloklar, italikler, denetciler), tespitler)
    if pdf_yolu:
        tespitler = _yalniz_isaretsizlere(lambda ts: alinti.pdf_ile_isaretle(pdf_yolu, bloklar, ts), tespitler)
    return eski_metin_sayfasi(tespitler, bloklar, denetciler)
