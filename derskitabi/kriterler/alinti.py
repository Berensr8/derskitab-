"""Alıntı ayırma (F2, K28): kitaba başka bir yazardan alınmış metinleri (şiir, hikâye parçası, eski
metin, makale) bulur. Bu metinlerdeki kelime tespitleri kitabın yazım hatası değil, yazarın kendi
yazımı ya da eski Türkçe olabilir; silinmez, düşük önceliğe iner (K25 ile aynı yol).

Bir blok iki yoldan alıntı sayılır:
  1. İmza satırı: alıntıların altında yazarın adı olur ("Hüseyin Nihal Atsız", "Nâzım Hikmet, Bütün
     Şiirleri", "Anonim (haz.: …)"). İmza satırı kısa, büyük harfle başlar, cümle gibi bitmez,
     üstündeki metinden küçük puntodadır, ilk kelimesi bir addır ve sağa yaslıdır (sağ kenarı metinle hizalı,
     sol kenarı metnin epey sağında). İmzanın üstünde, aynı sütunda ve aynı yazı tipindeki
     bloklar yukarı doğru alıntı sayılır ("(...)" atlama işaretleri araya girebilir).
  2. Eski dil: blokta Farsça tamlama ("kandîl-i sipihr") ya da "u/ü" bağlacı ("tâc u taht") var
     ve araçların tanımadığı en az 2 küçük harfli kelime geçiyor.
Yazı tipi ve punto PDF'ten okunur (her sayfa bir kez).
"""

import functools
import re
from collections import Counter
from dataclasses import replace

import pymupdf

from ..model import Blok, Tespit
from ..pdf_cikarma import _OKUMA_AYARLARI
from . import yazim

DUSUK_GUVEN = 0.25  # yazım hakemindeki "muhtemelen doğru" ile aynı (K25)
IMZA_EN_FAZLA_KARAKTER = 90
IMZA_EN_FAZLA_BOSLUK = 14  # sola hizalı imza ile üstündeki metin arası (punto)
IMZA_EN_KUCUK_PUNTO = 6  # harita etiketleri (2-4 punto) imza sayılmaz
IZAFET = re.compile(r"(?<![\w’'])[a-zçğıöşüâîû][^\W\d_]*-[ıiuü](?=[\s,.;:!?]|$)")
BAGLAC = re.compile(r"[^\W\d_]\s[uü]\s[^\W\d_]")
ATLAMA = re.compile(r"^\(?\s*(?:…|\.\.\.)\s*\)?$")
KUCUK_KELIME = re.compile(r"(?<![\w’'])[a-zçğıöşüâîû][^\W\d_]{2,}")
ALINTI_NOTU = "Alıntı metin"


def sayfa_bicimleri(sayfa: pymupdf.Page) -> dict:
    """{yuvarlanmış bbox: (yazı tipi, punto)} — bloktaki en çok karakterli biçim."""
    sonuc = {}
    for bl in sayfa.get_text("dict", flags=_OKUMA_AYARLARI)["blocks"]:
        c = Counter()
        for satir in bl.get("lines", []):
            for s in satir["spans"]:
                c[(s["font"].split("+")[-1], round(s["size"]))] += len(s["text"].strip())
        if c:
            sonuc[tuple(round(v) for v in bl["bbox"])] = c.most_common(1)[0][0]
    return sonuc


def blok_bicimleri(pdf_yolu, bloklar: list[Blok]) -> dict:
    """{(sayfa_no, blok_no): (yazı tipi, punto) ya da None}"""
    sonuc = {}
    with pymupdf.open(pdf_yolu) as belge:
        for no in sorted({b.sayfa_no for b in bloklar}):
            bicim = sayfa_bicimleri(belge[no - 1])
            for b in bloklar:
                if b.sayfa_no == no:
                    sonuc[(b.sayfa_no, b.blok_no)] = bicim.get(tuple(round(v) for v in b.bbox))
    return sonuc


def _ustteki(b: Blok, sayfa_bloklari: list[Blok]) -> Blok | None:
    """Aynı sütunda (yatayda örtüşen) hemen üstteki blok. İmza satırı üstündeki metnin kutusuyla
    birkaç punto üst üste binebiliyor (TDE 10 s.38), bu yüzden 6 punto örtüşmeye izin verilir."""
    adaylar = [x for x in sayfa_bloklari if x is not b and x.bbox[1] < b.bbox[1] - 1
               and x.bbox[3] <= b.bbox[1] + 6 and x.bbox[0] < b.bbox[2] and x.bbox[2] > b.bbox[0]]
    return max(adaylar, key=lambda x: x.bbox[3]) if adaylar else None


_PARANTEZ = re.compile(r"\([^)]*\)?")
_BAGLACLAR = {"ile", "ve", "de", "da", "u", "ü", "ve’"}


_SOYADI = re.compile(r"(?:oğlu|oğlan|zade)$")


@functools.cache
def _ad_turu(kelime: str) -> str:
    """"kesin": yalnız özel ad (Mustafa, Tahir, Cezmi) ya da soyadı eki (Eyüboğlu, Karacaoğlan,
    Recaizade); "olabilir": sıradan kelime de olabilen ad (Kemal, Kaplan) ya da sözlükte olmayan
    büyük harfli kelime (Alatlı, Pekolcay); "tamlama": iyelik ekli isim (Dağları, Zaferi, Destanı,
    Kutusu — yer ve başlık adlarının son kelimesi); "degil": sıradan kelime (Azar, Atsız, Bilgi)."""
    if len(kelime) < 3 or kelime.isupper():
        return "degil"
    if _SOYADI.search(kelime):
        return "kesin"
    cozumler = yazim.starlang_cozumleyici().morphologicalAnalysis(kelime)
    if cozumler.size() == 0:
        return "olabilir"
    parcalar = [cozumler.getFsmParse(i).transitionList() for i in range(cozumler.size())]
    if any("+P3SG+NOM" in c or "+P3PL+NOM" in c for c in parcalar):
        return "tamlama"
    prop = ["+PROP" in c for c in parcalar]
    return "kesin" if all(prop) else "olabilir" if any(prop) else "degil"


def ad_gibi_mi(metin: str) -> bool:
    """Yazar adı gibi mi ("Hüseyin Nihal Atsız", "Nâzım Hikmet, Bütün Şiirleri", "Anonim (haz.: …)").
    Virgülden önceki ad kısmı: rakam yok, 2-5 kelime, hepsi büyük harfle başlıyor, son kelime iyelik
    ekli değil; kelimelerin hepsi ad olabilir ya da en fazla biri sıradan ve en az biri kesin ad.
    Tek kelimelik imza yalnız "Anonim" ya da soyadı (Karacaoğlan).
    Elenenler: "Görsel 1.19", "Bilgi Kutusu", "Altay Dağları", "Ergenekon Destanı", "Trabzon"."""
    if any(c.isdigit() for c in _PARANTEZ.sub(" ", metin)):
        return False
    ad = _PARANTEZ.sub(" ", metin).split(",")[0]
    kelimeler = [k.split("’")[0].split("-")[0] for k in ad.split() if k not in _BAGLACLAR]
    if not kelimeler or len(kelimeler) > 5 or not all(k[:1].isupper() for k in kelimeler):
        return False
    if kelimeler[0] == "Anonim":
        return True
    if len(kelimeler) == 1:
        return bool(_SOYADI.search(kelimeler[0]))
    turler = [_ad_turu(k) for k in kelimeler]
    if turler[-1] == "tamlama":  # yer ve başlık adı ("Altay Dağları"); "Bedri Rahmi" gibi adlar ilk kelimelerde
        return False
    turler = ["olabilir" if t == "tamlama" else t for t in turler]
    return turler.count("degil") == 0 or (turler.count("degil") == 1 and "kesin" in turler)


def imza_mi(b: Blok, ust: Blok | None, bicim, ust_bicim) -> bool:
    metin = b.metin.strip()
    if ust is None or not bicim or not ust_bicim or not ad_gibi_mi(metin):
        return False
    if len(metin) > IMZA_EN_FAZLA_KARAKTER or metin[-1] in ".:?!;,*":
        return False
    if not IMZA_EN_KUCUK_PUNTO <= bicim[1] < ust_bicim[1]:  # imza metinden küçük ama okunur puntoda
        return False
    # Üstte gerçek bir metin olmalı: en az 8 kelime, kelimelerin en az %40'ı küçük harfle başlıyor
    # (harita etiketleri — "Bakü - Tiflis - Ceyhan Ham Petrol Boru Hattı" — elenir)
    ust_kelimeler = [k for k in ust.metin.split() if k[:1].isalpha()]
    if len(ust_kelimeler) < 8 or sum(k[0].islower() for k in ust_kelimeler) < 0.4 * len(ust_kelimeler):
        return False
    # Konum: metnin sağına girintili (çoğu imza) ya da sola hizalı ve hemen altında (iki sütunlu şiirler)
    girintili = b.bbox[0] - ust.bbox[0] >= 30
    sola_hizali_altta = abs(b.bbox[0] - ust.bbox[0]) <= 5 and b.bbox[1] - ust.bbox[3] <= IMZA_EN_FAZLA_BOSLUK
    return girintili or sola_hizali_altta


def eski_dil_mi(b: Blok, denetciler) -> bool:
    """Farsça tamlama ("kandîl-i") ya da "u/ü" bağlacı var ve araçların tanımadığı en az 2 küçük
    harfli kelime geçiyor."""
    if not (IZAFET.search(b.metin) or BAGLAC.search(b.metin)):
        return False
    taninmayan = [k for k in KUCUK_KELIME.findall(b.metin)
                  if not (yazim._gecerli(denetciler[0], k) and yazim._gecerli(denetciler[1], k))]
    return len(taninmayan) >= 2


def alinti_bloklari(bloklar: list[Blok], bicimler: dict, denetciler=None) -> dict:
    """{(sayfa_no, blok_no): sebep} — sebep imzanın metni ya da "eski dil"."""
    denetciler = denetciler or yazim.varsayilan_denetciler()
    sayfalar = {}
    for b in bloklar:
        sayfalar.setdefault(b.sayfa_no, []).append(b)
    sonuc = {}
    for sayfa_bloklari in sayfalar.values():
        for b in sayfa_bloklari:
            ust = _ustteki(b, sayfa_bloklari)
            bicim = bicimler.get((b.sayfa_no, b.blok_no))
            if not imza_mi(b, ust, bicim, bicimler.get((ust.sayfa_no, ust.blok_no)) if ust else None):
                continue
            alinti_bicimi = bicimler.get((ust.sayfa_no, ust.blok_no))
            while ust is not None:  # imzadan yukarı: aynı biçimdeki bloklar ve atlama işaretleri
                ust_bicim = bicimler.get((ust.sayfa_no, ust.blok_no))
                if ust_bicim == alinti_bicimi:
                    sonuc[(ust.sayfa_no, ust.blok_no)] = b.metin.strip()
                elif not ATLAMA.match(ust.metin.strip()):
                    break
                ust = _ustteki(ust, sayfa_bloklari)
        for b in sayfa_bloklari:
            if (b.sayfa_no, b.blok_no) not in sonuc and b.tur in ("paragraf", "kisa") and eski_dil_mi(b, denetciler):
                sonuc[(b.sayfa_no, b.blok_no)] = "eski dil"
    return sonuc


def alintilari_isaretle(tespitler: list[Tespit], alintilar: dict) -> list[Tespit]:
    """Alıntı bloklarındaki kelime tespitleri düşük önceliğe iner (silinmez); TDK kurallarına
    dokunulmaz (noktalama boşluğu gibi dizgi hataları alıntıda da kitabın hatasıdır)."""
    sonuc = []
    for t in tespitler:
        sebep = alintilar.get((t.sayfa_no, t.blok_no))
        if t.alt_tur != "morfoloji" or sebep is None:
            sonuc.append(t)
            continue
        kaynak = "eski Türkçe ya da edebî dil işaretleri var" if sebep == "eski dil" else f"kaynak: {sebep}"
        sonuc.append(replace(t, guven_skoru=min(t.guven_skoru, DUSUK_GUVEN), aciklama=t.aciklama +
                             f" {ALINTI_NOTU} ({kaynak}): kelime yazarın kendi yazımı ya da eski yazım olabilir"
                             " — düşük öncelik."))
    return sonuc
