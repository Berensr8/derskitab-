"""PDF okuma parçası (K29): kitabın değil, PDF'ten metin çıkarmanın ürettiği "kelimeler".

Morfoloji araçları parçalanmış kelimeyi hata sayar; yazım hakemi de (K25) bunlara "hata" ya da
"belirsiz" diyordu (her MEB kitabında İstiklal Marşı/Gençliğe Hitabe sayfası: "ymetli", "lmak").
Tespit silinmez; güveni düşer ve sebebi açıklamaya yazılır. Dört durum (yalnız metinden; boşluk
genişliği ölçülmez — PDF'te gerçek kelime arası ile parçalar arası aynı genişlikte çıktı):
  1. Özel glif: kelimeye bitişik, yazı tipine özgü bir işaret (U+F0F5 gibi özel kullanım alanı
     karakteri). Bu kitaplarda "ı" harfi böyle kaydedilmiş: "k<U+F0F5>ymetli".
  2. Rakama bitişik: "180°den" → "180cden" (derece işareti harf okunmuş); "1960’larda" (sayıya
     getirilen ek, kendi başına kelime değil).
  3. Düşmüş harf: komşu parçayla arasına tek bir harf girince geçerli kelime oluyor
     ("dikd" + "ö" + "rtgen" = dikdörtgen; yazı tipi bir harfi kaydetmemiş).
  4. Blok sınırında bölünmüş: TDK kural tespitindeki son kelime bloğun son kelimesi ve sonraki
     bloğun ilk kelimesiyle birleşince geçerli ("örgüsüne da" + "ha" → "daha").
Komşu parçayla aynı satırda araya harf girmeden birleşince geçerli kelime oluyorsa ("eşitlik leri")
kitapta da boşluk görünüyor: bu bir dizgi hatası olabilir; tespit indirilmez, açıklamaya
birleşik yazımı eklenir.
"""

import re
import unicodedata
from dataclasses import replace

from ..model import Blok, Tespit
from . import yazim

DUSUK_GUVEN = 0.25  # alıntı ayırma ve yazım hakemindeki düşük öncelikle aynı (K25, K28)
PARCA_NOTU = "PDF okuma parçası"
_HARFLER = "abcçdefgğhıijklmnoöprsştuüvyzâîû"
_KURAL_TURLERI = ("bag_de_da_uyum", "bag_te_ta", "soru_eki_uyum")


def _ozel_glif(c: str) -> bool:
    return bool(c) and (unicodedata.category(c) in ("Co", "Cn") or c == "�")


def _gecerli(kelime: str, denetciler) -> bool:
    return all(yazim._gecerli(d, kelime) for d in denetciler)


def _komsular(metin: str, bas: int, son: int) -> tuple[str, str]:
    """Kelimenin yalnız boşlukla ayrılmış önceki ve sonraki harf dizisi (yoksa "")."""
    onceki = re.search(r"([^\W\d_]+)[ \t\n]+$", metin[:bas])
    sonraki = re.match(r"[ \t\n]+([^\W\d_]+)", metin[son:])
    return (onceki.group(1) if onceki else ""), (sonraki.group(1) if sonraki else "")


def _birlesik(sol: str, sag: str, denetciler, harf_ekle: bool) -> str | None:
    if not sol or not sag:
        return None
    adaylar = [sol + h + sag for h in _HARFLER] if harf_ekle else [sol + sag]
    return next((a for a in adaylar if _gecerli(a, denetciler)), None)


def kelime_sebebi(metin: str, kelime: str, denetciler) -> tuple[str | None, str]:
    """(indirme sebebi ya da None, açıklamaya eklenecek not). Kelimenin metindeki ilk bitişik
    geçişine bakılır (aynı kelime blokta birden çok geçebilir)."""
    for m in re.finditer(rf"(?<![^\W\d_]){re.escape(kelime)}(?![^\W\d_])", metin):
        once, sonra = metin[m.start() - 1:m.start()], metin[m.end():m.end() + 1]
        if _ozel_glif(once) or _ozel_glif(sonra):
            return "kelimeye bitişik özel bir yazı tipi işareti var (PDF'te bir harf, ör. 'ı', böyle kaydedilmiş)", ""
        if once.isdigit():
            return "rakama bitişik (derece ya da birim işareti harf olarak okunmuş olabilir)", ""
        if once and once in "'’" and metin[m.start() - 2:m.start() - 1].isdigit():
            return "sayıya getirilen ek (1960’larda gibi), kendi başına kelime değil", ""
        sol, sag = _komsular(metin, m.start(), m.end())
        for a, b in ((sol, kelime), (kelime, sag)):
            if (bulunan := _birlesik(a, b, denetciler, harf_ekle=True)):
                return f"komşu parçayla arasına tek harf girince '{bulunan}' oluyor (yazı tipi bir harfi kaydetmemiş)", ""
        for a, b in ((sol, kelime), (kelime, sag)):
            if (bulunan := _birlesik(a, b, denetciler, harf_ekle=False)):
                return None, (f" '{a} {b}' birleşince '{bulunan}' oluyor: kelime kitapta ayrı yazılmış ya da satır "
                              f"sonunda bölünmüş olabilir.")
    return None, ""


def blok_siniri_sebebi(t: Tespit, metin: dict, denetciler) -> str | None:
    """Kural tespitinin son kelimesi bloğun son kelimesiyse ve sonraki blokla birleşiyorsa."""
    son = (t.metin_parcasi or "").split()[-1:] or [""]
    blok = metin.get((t.sayfa_no, t.blok_no), "").rstrip()
    sonraki = re.match(r"\s*([^\W\d_]+)", metin.get((t.sayfa_no, t.blok_no + 1), ""))
    if not son[0] or not blok.endswith(son[0]) or not sonraki:
        return None
    if (bulunan := _birlesik(son[0], sonraki.group(1), denetciler, harf_ekle=False)):
        return f"blok sonunda bölünmüş kelime ('{son[0]}' + '{sonraki.group(1)}' = '{bulunan}')"
    return None


def isaretle(tespitler: list[Tespit], bloklar: list[Blok], denetciler=None) -> list[Tespit]:
    """PDF okuma parçası olan yazım tespitlerini düşük önceliğe indirir; yeni liste döner."""
    denetciler = denetciler or yazim.varsayilan_denetciler()
    metin = {(b.sayfa_no, b.blok_no): b.metin for b in bloklar}
    sonuc = []
    for t in tespitler:
        sebep, ek = None, ""
        if t.alt_tur == "morfoloji" and t.metin_parcasi:
            sebep, ek = kelime_sebebi(metin.get((t.sayfa_no, t.blok_no), ""), t.metin_parcasi, denetciler)
        elif t.alt_tur in _KURAL_TURLERI:
            sebep = blok_siniri_sebebi(t, metin, denetciler)
        if sebep:
            sonuc.append(replace(t, guven_skoru=min(t.guven_skoru, DUSUK_GUVEN),
                                 aciklama=f"{t.aciklama} {PARCA_NOTU}: {sebep} — kitabın değil, PDF okumanın sorunu olabilir."))
        else:
            sonuc.append(replace(t, aciklama=t.aciklama + ek) if ek else t)
    return sonuc
