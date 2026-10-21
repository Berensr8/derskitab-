"""Terim tanıma (K29): araçların bilmediği ama kitabın kendisinin terim olarak gösterdiği kelimeler.

Biyoloji kitaplarında kelime tespitlerinin çoğu terim ve Latince addı (K29 körlemesine örneklem:
100 tespitin 83'ü). Kitap bunları iki yoldan kendisi işaretliyor:
  1. Sözlük: "terim: açıklama" biçimindeki maddeler (kitabın sonundaki Sözlük, TDE'de metinlerin
     altındaki kelime açıklamaları). Tespit edilen kelime bir maddenin kendisi ya da ek almış hâli.
  2. İtalik: bilimsel adlar italik dizilir ("Vanessa cardui"); hemen arkasındaki parantez içi de
     adın okunuşudur ("(vanesa karduyi)"). Yazı biçimi PDF'ten okunur.
Tespit silinmez; güveni düşer, sebebi açıklamaya yazılır (editör yine görebilir).
"""

import re
from collections import defaultdict
from dataclasses import replace

import pymupdf

from ..model import Blok, Tespit
from ..pdf_cikarma import _OKUMA_AYARLARI
from . import yazim

DUSUK_GUVEN = 0.25
TERIM_NOTU = "Terim"
EN_KISA_KOK = 4  # sözlük maddesinin ek almış hâli: madde en az bu uzunlukta olmalı
_MADDE = re.compile(r"^\s*([a-zçğıöşüâîû][^\W\d_]*(?:[ -][^\W\d_]+){0,3})\s*(?:\([^)]{1,40}\)\s*)?:\s+\S")
_ITALIK = 2  # PyMuPDF span bayrağı
# Bloğun bu oranından fazlası italikse italik bir işaret değil, bloğun biçimidir (başlık, yönerge): o
# bloktaki kelimeler italik diye terim sayılmaz (Biyoloji 11'in italik kazanım başlığındaki
# "sorumluklar" yazım hatası terim sanıldı — K29 testi)
ITALIK_EN_FAZLA_ORAN = 0.6


def sozluk_maddeleri(bloklar: list[Blok]) -> set[str]:
    """Kitaptaki "kelime: açıklama" maddelerinin kelimeleri (Türkçe küçük harfle)."""
    maddeler = set()
    for b in bloklar:
        if (m := _MADDE.match(b.metin)):
            maddeler |= {yazim.tr_kucuk(k) for k in re.split(r"[ -]", m.group(1)) if len(k) >= 3}
    return maddeler


def sozlukte_mi(kelime: str, maddeler: set[str], bilinen=None) -> str | None:
    """Kelime bir sözlük maddesi ya da ek almış hâli mi? Ek almış hâl yalnız araçların tanımadığı
    maddelerde aranır (bilinen: kelime -> araç tanıyor mu): bilinen bir kelimenin ekli hâli zaten
    geçerli olurdu; "etme" maddesi "etmeize" yazım hatasını terim yapıyordu (K23 recall seti)."""
    k = yazim.tr_kucuk(kelime)
    if k in maddeler:
        return k
    return next((k[:i] for i in range(len(k) - 1, EN_KISA_KOK - 1, -1)
                 if k[:i] in maddeler and not (bilinen and bilinen(k[:i]))), None)


def italik_kelimeler(pdf_yolu, bloklar: list[Blok], sayfalar: set[int]) -> dict:
    """{(sayfa_no, blok_no): italik yazılmış kelimeler} — yalnız verilen sayfalar okunur. Çoğu italik
    olan bloklar (ITALIK_EN_FAZLA_ORAN) alınmaz."""
    sonuc = defaultdict(set)
    with pymupdf.open(pdf_yolu) as belge:
        for no in sorted(sayfalar):
            kutular = {tuple(round(v) for v in b.bbox): b.blok_no for b in bloklar if b.sayfa_no == no}
            for bl in belge[no - 1].get_text("dict", flags=_OKUMA_AYARLARI)["blocks"]:
                blok_no = kutular.get(tuple(round(v) for v in bl["bbox"]))
                if blok_no is None:
                    continue
                italik, toplam, kelimeler = 0, 0, set()
                for satir in bl.get("lines", []):
                    for s in satir["spans"]:
                        n = len(s["text"].strip())
                        toplam += n
                        if s["flags"] & _ITALIK or re.search(r"italic|oblique", s["font"], re.I):
                            italik += n
                            kelimeler |= {yazim.tr_kucuk(k) for k in yazim._KELIME.findall(s["text"])}
                if kelimeler and italik <= ITALIK_EN_FAZLA_ORAN * toplam:
                    sonuc[(no, blok_no)] |= kelimeler
    return sonuc


def okunus_kelimeleri(metin: str, italikler: set[str]) -> set[str]:
    """İtalik bir kelimenin hemen arkasındaki parantezin içindeki kelimeler (adın okunuşu)."""
    sonuc = set()
    for m in re.finditer(r"([^\W\d_]+)\s*\(([^()]{1,80})\)", metin):
        if yazim.tr_kucuk(m.group(1)) in italikler:
            sonuc |= {yazim.tr_kucuk(k) for k in yazim._KELIME.findall(m.group(2))}
    return sonuc


def isaretle(tespitler: list[Tespit], bloklar: list[Blok], italikler: dict | None = None,
             denetciler=None) -> list[Tespit]:
    """Terim olan kelime tespitlerini düşük önceliğe indirir; yeni liste döner.
    italikler: italik_kelimeler() çıktısı (verilmezse yalnız sözlük kullanılır)."""
    denetciler = denetciler or yazim.varsayilan_denetciler()
    maddeler = sozluk_maddeleri(bloklar)
    metin = {(b.sayfa_no, b.blok_no): b.metin for b in bloklar}
    italikler = italikler or {}
    sonuc = []
    for t in tespitler:
        sebep = None
        if t.alt_tur == "morfoloji" and t.metin_parcasi:
            k = yazim.tr_kucuk(t.metin_parcasi)
            italik = italikler.get((t.sayfa_no, t.blok_no), set())
            if (madde := sozlukte_mi(t.metin_parcasi, maddeler, lambda m: yazim._gecerli(denetciler[0], m))):
                sebep = f"kitabın sözlüğünde açıklanmış ('{madde}')"
            elif k in italik:
                sebep = "italik yazılmış (bilimsel ad ya da yabancı kelime)"
            elif k in okunus_kelimeleri(metin.get((t.sayfa_no, t.blok_no), ""), italik):
                sebep = "italik yazılmış bir adın parantez içindeki okunuşu"
        sonuc.append(replace(t, guven_skoru=min(t.guven_skoru, DUSUK_GUVEN),
                             aciklama=f"{t.aciklama} {TERIM_NOTU}: {sebep} — araçların sözlüğünde yok, "
                                      f"yazım hatası olma ihtimali düşük.") if sebep else t)
    return sonuc
