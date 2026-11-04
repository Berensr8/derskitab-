"""Hatasız cümleye kitaplarda gerçekten görülen türde yapay yazım hatası ekleme (K33).

Hata türleri ve kitaplardaki örnekleri:
  HARF          düşme ("hazılayabilirsiniz"), ikileme ("söyleyebillirsiniz"), yer değiştirme ("rolleirn"),
                komşu tuş, Türkçe harf kaybı ("kisisel"), ters Türkçe harf ("ıçin"), hece tekrarı
                ("olacacağını"), hece düşmesi ("sorumluklar"), ek ikilemesi ("planınında")
  BITISIK_AYRI  bağlaç de/da, ki, soru eki mi bitişik; hâl eki -de ayrı; birleşik kelimeler ("bir çok");
                iki kelime boşluksuz; kelime ortadan bölünmüş
  BUYUK_KUCUK   cümle başı ya da özel ad küçük harfle
  KURAL_DIGER   kesme işareti düşmüş ("Türkiyenin"), cins ada kesme ("ev'de"), de/da uyumu ("çok de")

Ortaya çıkan kelime bazen geçerli bir Türkçe kelimedir ("kır" → "kir"): bunlar da hata olarak etiketlenir;
morfoloji araçlarının göremediği, modelin bağlamdan öğrenmesi gereken tür.
"""

import random
import re

from .etiketler import SINIF_NO

_HARF = re.compile(r"[^\W\d_]+")
_SADE = str.maketrans("ıİşŞğĞçÇöÖüÜ", "iIsSgGcCoOuU")
_TERS = {"i": "ı", "ı": "i", "s": "ş", "g": "ğ", "c": "ç", "o": "ö", "u": "ü", "ş": "s", "ç": "c", "ö": "o", "ü": "u"}
_KLAVYE = ["qwertyuıopğü", "asdfghjklşi", "zxcvbnmöç"]
_KOMSU = {}
for _sira in _KLAVYE:
    for _i, _h in enumerate(_sira):
        _KOMSU[_h] = (_sira[_i - 1] if _i else "") + (_sira[_i + 1] if _i + 1 < len(_sira) else "")
_UNLU = set("aeıioöuü")
BAGLAC = {"de", "da", "ki", "mi", "mı", "mu", "mü"}
BIRLESIK = ["herhangi", "birçok", "birkaç", "hiçbir", "birbiri", "birbirine", "birbirinden", "birbirini",
            "herkes", "hiçbiri", "birtakım", "kendiliğinden", "pekçok", "olabilir", "yapabilir", "bilgisayar",
            "başöğretmen", "hanımeli", "karadeniz", "akdeniz", "cumhurbaşkanı", "başbakan", "yüzyıl"]


def _kelime_mi(k: str, en_az: int = 3) -> bool:
    return bool(_HARF.fullmatch(k)) and len(k) >= en_az and not k.isupper()


def _ic(k: str, r: random.Random) -> int:
    """Kelimenin içinden (ilk harf değil) bir konum."""
    return r.randrange(1, len(k))


def harf_hatasi(k: str, r: random.Random) -> str | None:
    tur = r.choices(["dusme", "ikileme", "yer", "komsu", "tr", "ters", "hece_tekrar", "hece_dusme", "ek"],
                    [18, 14, 12, 10, 18, 6, 7, 7, 8])[0]
    if tur == "dusme":
        i = _ic(k, r)
        y = k[:i] + k[i + 1:]
    elif tur == "ikileme":
        i = _ic(k, r)
        y = k[:i] + k[i] + k[i:]
    elif tur == "yer":
        i = r.randrange(1, len(k) - 1)
        y = k[:i] + k[i + 1] + k[i] + k[i + 2:]
    elif tur == "komsu":
        i = _ic(k, r)
        aday = _KOMSU.get(k[i].lower(), "")
        y = k[:i] + r.choice(aday) + k[i + 1:] if aday else None
    elif tur == "tr":
        yerler = [i for i, h in enumerate(k) if h in "ıİşŞğĞçÇöÖüÜ"]
        if not yerler:
            return None
        sec = r.sample(yerler, min(len(yerler), r.choice([1, 1, 2, len(yerler)])))
        y = "".join(h.translate(_SADE) if i in sec else h for i, h in enumerate(k))
    elif tur == "ters":
        yerler = [i for i, h in enumerate(k) if h in _TERS and i > 0]
        if not yerler:
            return None
        i = r.choice(yerler)
        y = k[:i] + _TERS[k[i]] + k[i + 1:]
    elif tur == "hece_tekrar":  # olacağını → olacacağını
        if len(k) < 6:
            return None
        i = r.randrange(2, len(k) - 2)
        y = k[:i] + k[i - 2:i] + k[i:]
    elif tur == "hece_dusme":  # sorumluluklar → sorumluklar
        if len(k) < 7:
            return None
        i = r.randrange(2, len(k) - 3)
        y = k[:i] + k[i + 2:]
    else:  # ek ikilemesi: planında → planınında
        if len(k) < 6:
            return None
        n = r.choice([2, 3])
        y = k[:-1] + k[-n - 1:-1] + k[-1] if r.random() < 0.5 else k[:-n] + k[-n:] + k[-n:]
    return y if y and y != k else None


def hata_ekle(kelimeler: list[str], r: random.Random, en_fazla: int = 2) -> tuple[list[str], list[int]] | None:
    """Cümleye 1..en_fazla hata ekler. Döner: (yeni kelimeler, etiketler) ya da uygun yer yoksa None."""
    k = list(kelimeler)
    e = [0] * len(k)
    hedef = r.choice([1] * 6 + [2] * 3 + [3]) if en_fazla >= 3 else r.choice([1, 1, 2][:en_fazla + 1])
    eklenen, deneme = 0, 0
    while eklenen < hedef and deneme < 20:
        deneme += 1
        i = r.randrange(len(k))
        if e[i] or (i + 1 < len(k) and e[i + 1]) or (i and e[i - 1]):
            continue
        sinif = r.choices(["HARF", "BITISIK_AYRI", "BUYUK_KUCUK", "KURAL_DIGER"], [62, 22, 6, 10])[0]
        bas, govde, son = _ayir(k[i])
        if sinif == "HARF":
            if not _kelime_mi(govde, 4):
                continue
            y = harf_hatasi(govde, r)
            if not y:
                continue
            k[i], e[i] = bas + y + son, SINIF_NO["HARF"]
        elif sinif == "BITISIK_AYRI":
            sonuc = _bitisik_ayri(k, e, i, r)
            if sonuc is None:
                continue
            k, e = sonuc
        elif sinif == "BUYUK_KUCUK":
            if not (_kelime_mi(govde, 2) and govde[0].isupper() and not bas):
                continue
            k[i], e[i] = bas + govde[0].lower().replace("i̇", "i") + govde[1:] + son, SINIF_NO["BUYUK_KUCUK"]
            if govde[0] == "İ":
                k[i] = bas + "i" + govde[1:] + son
        else:
            y = _kural(govde, k, i, r)
            if not y:
                continue
            k[i], e[i] = bas + y + son, SINIF_NO["KURAL_DIGER"]
        eklenen += 1
    return (k, e) if eklenen else None


_NOKTALAMA = "\"'“”‘’«»()[]{}.,;:!?…-–—/"


def _ayir(k: str) -> tuple[str, str, str]:
    govde = k.strip(_NOKTALAMA)
    if not govde or govde not in k:
        return "", k, ""
    i = k.index(govde)
    return k[:i], govde, k[i + len(govde):]


def _bitisik_ayri(k: list[str], e: list[int], i: int, r: random.Random):
    s = SINIF_NO["BITISIK_AYRI"]
    _, govde, _ = _ayir(k[i])
    alt = govde.lower()
    # bağlaç / soru eki bitişik yazılmış: "ben de" → "bende", "geldi mi" → "geldimi"
    if i > 0 and alt in BAGLAC and _ayir(k[i - 1])[2] == "" and _kelime_mi(_ayir(k[i - 1])[1], 2):
        return k[:i - 1] + [k[i - 1] + k[i]] + k[i + 1:], e[:i - 1] + [s] + e[i + 1:]
    # hâl eki -de/-da ayrı yazılmış: "evde" → "ev de"
    m = re.fullmatch(r"([^\W\d_]{3,})([dt][ae])", govde)
    if m and r.random() < 0.5:
        b, _, son = _ayir(k[i])
        return k[:i] + [b + m.group(1), m.group(2) + son] + k[i + 1:], e[:i] + [s, s] + e[i + 1:]
    # birleşik kelime ayrı yazılmış
    for b in BIRLESIK:
        if alt.startswith(b) and len(b) >= 5:
            for j in range(2, len(b) - 1):
                if b[:j] in ("her", "bir", "hiç", "kendi", "pek", "ola", "yapa", "bilgi", "baş", "kara", "ak",
                             "cumhur", "yüz", "hanım"):
                    bas_, g, son = _ayir(k[i])
                    return (k[:i] + [bas_ + g[:j], g[j:] + son] + k[i + 1:], e[:i] + [s, s] + e[i + 1:])
    # iki kelime boşluksuz ya da bir kelime ortadan bölünmüş
    if r.random() < 0.5 and i + 1 < len(k) and _kelime_mi(govde, 2) and _kelime_mi(_ayir(k[i + 1])[1], 2) \
            and _ayir(k[i])[2] == "":
        return k[:i] + [k[i] + k[i + 1]] + k[i + 2:], e[:i] + [s] + e[i + 2:]
    if _kelime_mi(govde, 7) and not _ayir(k[i])[0]:
        j = r.randrange(3, len(govde) - 2)
        b, g, son = _ayir(k[i])
        return k[:i] + [g[:j], g[j:] + son] + k[i + 1:], e[:i] + [s, s] + e[i + 1:]
    return None


def _kural(govde: str, k: list[str], i: int, r: random.Random) -> str | None:
    if "'" in govde or "’" in govde:  # kesme işareti düşmüş
        return govde.replace("'", "").replace("’", "")
    alt = govde.lower()
    if alt in ("de", "da") and i > 0:  # bağlaç uyumu bozulmuş: "çok de"
        return {"de": "da", "da": "de", "De": "Da", "Da": "De"}.get(govde)
    m = re.fullmatch(r"([^\W\d_]{3,}?)((?:d|t)[ae]|[ıiuü]n|l[ae]r)", govde)
    if m and govde[0].islower() and r.random() < 0.4:  # cins ada kesme: "ev'de"
        return m.group(1) + "'" + m.group(2)
    return None
