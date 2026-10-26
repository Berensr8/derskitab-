"""Satır blokları (Faz 2 eki): PDF'te bazı kutularda her satır ayrı bir blok olarak okunur.

Biyografi kutuları, kenar notları ve bazı kitapların (TDE 12) bütün metni satır satır bloklara
bölünüyor; cümle satır başından başlıyor ve öznesi önceki blokta kalıyor ("…Orhan Veli'nin Garip" /
"tarzında yazdığı ilk şiirleri 1937'de…"). Bloklar değiştirilmez (blok numaraları kilitli test
setlerinde kullanılıyor); cümleye bakan kriterler ardışık satır bloklarını burada birleştirir.

Bir blok, hemen altındaki bloğa devam ediyor sayılır:
  - aynı sayfa, altındaki blok satır aralığı kadar yakın (boşluk ≤ 0,6 satır yüksekliği),
  - sol kenarlar hizalı (üstteki ilk satır girintili olabilir), üstteki satır sütunu dolduruyor,
  - cümle ortasında bitiyor: alttaki küçük harfle başlıyor ya da üstteki en az 5 kelimelik ve küçük
    harf ya da virgülle bitiyor (künye sayfalarındaki ad listeleri birleşmez),
  - alttaki bir liste maddesi değil ("a) …", "• …").
"""

import re

from .model import Blok

_SATIR_YUKSEKLIGI_EN_FAZLA = 16
_LISTE = re.compile(r"^\s*(?:[a-zçğıöşü]\)|[•▪◘\-–—])")
_SON_KELIME = re.compile(r"[^\W\d_]+$")
_SATIR_SONU_TIRESI = re.compile(r"(?<=[^\W\d_])[-‐‑¬]$")
_ILK_KELIME = re.compile(r"^[^\W\d_]+")


def devam_ediyor_mu(a: Blok, b: Blok) -> bool:
    """a bloğu (satırı) hemen altındaki b bloğunda devam ediyor mu?"""
    if a.sayfa_no != b.sayfa_no or a.tur not in ("paragraf", "kisa") or b.tur not in ("paragraf", "kisa"):
        return False
    bosluk = b.bbox[1] - a.bbox[3]
    satir = min(a.bbox[3] - a.bbox[1], _SATIR_YUKSEKLIGI_EN_FAZLA)
    hizali = b.bbox[0] - 3 <= a.bbox[0] <= b.bbox[0] + 25
    dolu = a.bbox[2] >= max(a.bbox[2], b.bbox[2]) - 15
    son = a.metin.rstrip()[-1:]
    yarim = b.metin.lstrip()[:1].islower() or ((son.islower() or son == ",") and len(a.metin.split()) >= 5)
    return -2 <= bosluk <= 0.6 * satir and hizali and dolu and yarim and not _LISTE.match(b.metin)


def satir_gruplari(bloklar: list[Blok]) -> list[list[Blok]]:
    """Blokları okuma sırasıyla gruplar: her grup birbirine devam eden satır bloklarıdır (çoğu tek blok)."""
    sayfalar: dict[int, list[Blok]] = {}
    for b in bloklar:
        sayfalar.setdefault(b.sayfa_no, []).append(b)
    sonraki = {}
    for sayfa_bloklari in sayfalar.values():
        for a in sayfa_bloklari:
            alttakiler = [b for b in sayfa_bloklari if b is not a and b.bbox[1] >= a.bbox[1] + 1]
            b = min(alttakiler, key=lambda x: (x.bbox[1], abs(x.bbox[0] - a.bbox[0])), default=None)
            if b is not None and devam_ediyor_mu(a, b):
                sonraki[id(a)] = b
    devami = {id(b) for b in sonraki.values()}
    gruplar = []
    for b in bloklar:
        if id(b) in devami:
            continue  # bir grubun içinde, baştaki blokla birlikte eklenir
        grup = [b]
        while id(grup[-1]) in sonraki and len(grup) < 200:
            grup.append(sonraki[id(grup[-1])])
        gruplar.append(grup)
    return gruplar


def grup_metni(grup: list[Blok], bilesik_mi=None, parca_mi=None) -> tuple[str, list[int]]:
    """(birleşik metin, her bloğun metindeki başlangıç konumu). Satır sonu tiresi ("top-" + "lumsal")
    alttaki satır küçük harfle başlıyorsa silinip kelime birleştirilir. bilesik_mi(kelime) verilirse
    tiresi hiç kaydedilmemiş kelimeler ("Ga" + "rip") de boşluksuz birleştirilir: birleşim geçerli bir
    kelimeyse ve parçalardan biri değilse. parca_mi: parçalar için (daha sıkı) ölçüt; verilmezse bilesik_mi
    ("yansı" + "ması": araçlardan biri "ması"yı da kelime sanıyor — parçalar iki araçla da sınanmalı)."""
    metin, baslar = "", []
    for b in grup:
        parca = b.metin.strip()
        if metin and _SATIR_SONU_TIRESI.search(metin):
            if parca[:1].islower():
                metin = metin[:-1]  # satır sonu tiresi; büyük harfle devam ediyorsa gerçek tire ("Türk-Yunan")
        elif metin:
            sol, sag = _SON_KELIME.search(metin), _ILK_KELIME.search(parca)
            ayri = True
            if bilesik_mi and sol and sag and sol.group(0)[-1:].islower():
                s, g = sol.group(0), sag.group(0)
                tek = parca_mi or bilesik_mi
                ayri = not (bilesik_mi(s + g) and not (tek(s) and tek(g)))
            metin += " " if ayri else ""
        baslar.append(len(metin))
        metin += parca
    return metin, baslar


def birlesik_bloklar(bloklar: list[Blok]) -> list[Blok]:
    """Her satır grubu tek blok olur: ilk bloğun numarası, kutuların birleşimi, birleşik metin.
    Tek bloklu gruplar olduğu gibi kalır."""
    from .pdf_cikarma import blok_turu
    sonuc = []
    for grup in satir_gruplari(bloklar):
        if len(grup) == 1:
            sonuc.append(grup[0])
            continue
        metin, _ = grup_metni(grup)
        kutu = (min(b.bbox[0] for b in grup), min(b.bbox[1] for b in grup),
                max(b.bbox[2] for b in grup), max(b.bbox[3] for b in grup))
        sonuc.append(Blok(grup[0].sayfa_no, grup[0].blok_no, kutu, metin, grup[0].basili_sayfa_no, blok_turu(metin)))
    return sonuc
