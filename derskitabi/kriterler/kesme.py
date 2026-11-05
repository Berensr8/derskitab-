"""Kesme işareti denetimi (K34). TDK "Kesme İşareti" kuralına göre:

  1. ozel_ad_kesme      Özel ada gelen iyelik, durum ve bildirme ekleri kesmeyle ayrılır:
                        "Türkistanda" → Türkistan'da, "Atatürkün" → Atatürk'ün, "Ankaradaki" → Ankara'daki.
  2. kisaltma_kesme     Kısaltmalara gelen ekler: "DNAnın" → DNA'nın, "ABDde" → ABD'de.
  3. sayi_kesme         Sayılara gelen ekler: "1923te" → 1923'te, "19uncu" → 19'uncu.
  4. gereksiz_kesme     Yapım ekleri ve çokluk eki kesmeyle ayrılmaz: "Türkçe'nin" → Türkçenin,
                        "Türkler'in" → Türklerin, "Konya'lı" → Konyalı.

Özel adı Zemberek tanır: kelimenin *bütün* çözümlemeleri "özel ad + çekim eki" olmalı. Kelimenin
özel ad olmayan bir okuması da varsa ("Doğuda": doğu/Doğu, "Birliğine": birlik) işaretlenmez —
TDK'nın kurum adı istisnası ("Türk Dil Kurumundan") ve cins ad olarak kullanılan kelimeler
böylece dışarıda kalır. Kaçırılan olur ama sahte tespit az olur.

Kitaptan kanıt (geliştirme sayfalarında görüldü): Zemberek'in sözlüğünde garip özel adlar var
("Karekod", "Akti", "Buyru" — "Karekodu", "Aktin", "Buyrun" özel ad + ek sanılıyordu). Bu yüzden
özel ad, kitabın başka bir yerinde kesmeyle yazılmışsa işaretlenir ("Tibet'e" yazan kitap
"Tibete" de yazmışsa). Tespit hem TDK'ya hem kitabın kendi yazımına aykırıdır. Ardından büyük
harfli bir kelime geliyorsa ("Halide Nusret", "Glorya Pastanesine") ek adın son kelimesine gelir,
işaretlenmez.
"""

import functools
import logging
import re
from collections import Counter
from collections.abc import Callable

from ..model import Blok, Tespit

# kelime -> Zemberek çözümlemeleri (format_string): "[Ankara:Noun, Prop] ankara:Noun+A3sg+da:Loc"
Cozumleyici = Callable[[str], list[str]]

_BUYUK = "A-ZÇĞİÖŞÜÂÎÛ"
_KUCUK = "a-zçğıöşüâîû"
_KESME = "'’"
CEKIM = {"Dat", "Loc", "Abl", "Acc", "Gen", "Ins", "P1sg", "P2sg", "P3sg", "P1pl", "P2pl", "P3pl"}
# Bildirme eki (ek fiil): "Ankaradır", "Almansınız", "Ahmetmiş"
BILDIRME = {"Cop", "A1sg", "A2sg", "A1pl", "A2pl", "Past", "Narr", "Cond"}
# Ay ve gün adlarında kesme yalnız belirli bir tarihte konur (TDK: "17 Aralık'a"); karar bağlama bağlı.
TARIH_ADLARI = {"ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim",
                "kasım", "aralık", "pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"}
# Özel ad sözlükte yapım ekiyle türemişse (Türkçe, Osmanlı, Konyalı) ekleri ayrılmaz.
_YAPIM_SONU = re.compile(r"(?:l[ıiuü]|[cç][ae]|l[ıiuü]k|[cç][ıiuü])$")
# Kısaltma ve sayıya gelen ekler (en az iki harf: "3a", "2x" gibi değişkenler karışmasın)
_EKLER = ("de da te ta den dan ten tan deki daki teki taki nin nın nun nün in ın un ün ye ya yi yı yu yü "
          "ne na ni nı nu nü le la yle yla ile dir dır dur dür tir tır tur tür dı di du dü tı ti tu tü "
          "inci ıncı uncu üncü nci ncı ncu ncü lik lık luk lük li lı lu lü ler lar e a i ı u ü").split()
_SAYI_EKI = re.compile(rf"(?<![\w.,/{_KESME}])(\d+)({'|'.join(e for e in _EKLER if len(e) >= 2)})(?![\w{_KESME}])")
_KISALTMA_EKI = re.compile(rf"(?<![\w{_KESME}])([{_BUYUK}]{{2,}})({'|'.join(_EKLER)})(?![\w{_KESME}])")
_KELIME = re.compile(rf"(?<![\w{_KESME}])[{_BUYUK}][{_KUCUK}]+(?![\w{_KESME}])")
_KESMELI = re.compile(rf"(?<![\w{_KESME}])([{_BUYUK}][{_KUCUK}]+)[{_KESME}]([{_KUCUK}]+)(?![\w{_KESME}])")
_GEREKSIZ_EK = re.compile(r"^(?:l[ae]r|l[ıiuü]|l[ıiuü]k|[cç][ıiuü]|l[ae]ş)")


@functools.cache
def _zemberek():
    from .yazim import zemberek_kok_sirasini_sabitle
    logging.getLogger("zemberek").setLevel(logging.ERROR)
    zemberek_kok_sirasini_sabitle()
    from zemberek import TurkishMorphology
    return TurkishMorphology.create_with_defaults()


@functools.cache
def zemberek_analizleri(kelime: str) -> list[str]:
    try:
        return [a.format_string() for a in _zemberek().analyze(kelime).analysis_results]
    except Exception:  # noqa: BLE001 — araç bu kelimede çökerse çözümleme yok say
        return []


def _parcala(analiz: str) -> tuple[str, bool, list[tuple[str, str]]]:
    """"[Ankara:Noun, Prop] ankara:Noun+A3sg+da:Loc|ki:Rel→Adj" → ("Ankara", True,
    [("+", "Noun"), ("+", "A3sg"), ("+", "Loc"), ("|", "Rel→Adj")])."""
    bas, _, govde = analiz.partition("] ")
    kok, _, nitelik = bas.lstrip("[").partition(":")
    parcalar = [(ayrac or "+", m.split(":")[-1]) for ayrac, m in re.findall(r"([+|]?)([^+|]+)", govde)]
    return kok, "Prop" in nitelik, parcalar


def _ozel_ad_cekimi(analiz: str) -> str | None:
    """Çözümleme "özel ad + çekim/bildirme eki" ise özel adın kendisi, değilse None."""
    kok, ozel, p = _parcala(analiz)
    if not ozel or len(p) < 3 or p[0][1] != "Noun" or p[1][1] != "A3sg":
        return None
    ayrac, ek = p[2]
    if ayrac == "+" and ek in CEKIM:
        return kok
    if ayrac == "|" and ek == "Zero→Verb" and any(e in BILDIRME for _, e in p[3:]):
        return kok
    return None


def _turemis_ozel_ad(kok: str, cozumle: Cozumleyici) -> bool:
    """"Osmanlı", "Türkçe", "Konyalı": özel ad + yapım eki (TDK: ekleri ayrılmaz)."""
    m = _YAPIM_SONU.search(kok)
    return bool(m) and any(_parcala(a)[1] for a in cozumle(kok[:m.start()]))


# K34 doğrulaması: isabet 31/46 = 0,67 (karar kuralı 0,50–0,70 → güven 0,5, "orta öncelik": kontrol edin).
# Sahtelerin çoğu eski metin aktarımı (Paşa’ların), adı "-ce" ile biten kişi (Meryemce’nin).
GUVEN = 0.5


def _tespit(blok: Blok, alt_tur: str, parca: str, aciklama: str) -> Tespit:
    return Tespit(sayfa_no=blok.sayfa_no, blok_no=blok.blok_no, bbox=blok.bbox, kriter="yazim",
                  aciklama=aciklama, guven_skoru=GUVEN, basili_sayfa_no=blok.basili_sayfa_no,
                  alt_tur=alt_tur, metin_parcasi=parca)


def ozel_ad_eki(kelime: str, cozumle: Cozumleyici) -> str | None:
    """Kesmesiz "özel ad + ek" ise doğru yazımı ("Türkistan'da"), değilse None."""
    analizler = cozumle(kelime)
    koklar = [_ozel_ad_cekimi(a) for a in analizler]
    if not analizler or None in koklar:
        return None  # özel ad olmayan bir okuması da var
    kok = max(koklar, key=len)
    if kok.lower() in TARIH_ADLARI or _turemis_ozel_ad(kok, cozumle):
        return None
    n = len(kok)
    if any(c in "âîûÂÎÛ" for c in kelime[n - 1:]):
        return None  # "Ömerî": şapkalı harf ek değildir (doğrulamadan sonra bulunan hata, K34 sonucu)
    if kelime[:n].lower() == kok.lower():
        return f"{kelime[:n]}'{kelime[n:]}"
    if kelime[:n - 1].lower() == kok[:n - 1].lower():  # yumuşama: "Kerküğe" — TDK: Kerkük'e
        return f"{kelime[:n - 1]}{kok[-1]}'{kelime[n:]}"
    return None


def yalniz_ozel_ad(kelime: str, cozumle: Cozumleyici) -> bool:
    """Kelimenin bütün okumaları özel ad mı? ("Türk" evet; "Ay" hayır: ay/Ay)"""
    analizler = cozumle(kelime)
    return bool(analizler) and all(_parcala(a)[1] for a in analizler)


def gereksiz_kesme(on: str, ek: str, cozumle: Cozumleyici) -> str | None:
    """"Konya'lı", "Türkler'in", "Türkçe'nin": kesme gereksizse sebebi, değilse None.
    "-lı" ile biten adlar (Osmanlı'nın) işaretlenmez: TDK'nın kendi örneği "Karakeçili'nin"."""
    if _GEREKSIZ_EK.match(ek):
        return "yapım ekleri ve çokluk eki kesmeyle ayrılmaz"
    analizler = cozumle(on)
    sozlukte_kendisi = any(_parcala(a)[0].lower() == on.lower() for a in analizler)
    if re.search(r"l[ae]r$", on) and not sozlukte_kendisi and yalniz_ozel_ad(on[:-3], cozumle):
        return "çokluk eki ve sonraki ekler kesmeyle ayrılmaz"  # "Türkler'in" (ama "Alpler'de": dağ adı)
    if re.search(r"[cç][ae]$", on) and yalniz_ozel_ad(on[:-2], cozumle):
        return "yapım eki (-ca/-ce) ve sonraki ekler kesmeyle ayrılmaz"  # "Türkçe'nin", "İngilizce'de"
    return None


_SERT = {"b": "p", "c": "ç", "d": "t", "ğ": "k", "g": "k"}
_SONRAKI_AD = re.compile(rf"[ \t]+[{_BUYUK}][{_KUCUK}]")


def eser_listesinde(metin: str, konum: int) -> bool:
    """"Yâd, Arz-ı Hal, Türkiyem, Dünyanın En Güzel Arabistanı": virgülle ayrılmış, bütün kelimeleri
    büyük harfle başlayan en az üç parçalık bir dizinin içinde mi? (eser adları; ad değişmez)"""
    parcalar = re.split(r"([,;]|[.!?]\s)", metin)  # [parça, ayraç, parça, ayraç, …]
    bas, dizi, sira = 0, [], None
    for j, p in enumerate(parcalar):
        if j % 2 == 0:
            kelimeler = re.findall(r"[^\W\d_]+", p)
            dizi.append(bool(kelimeler) and all(k[0].isupper() for k in kelimeler))
            if sira is None and konum < bas + len(p):
                sira = len(dizi) - 1
        bas += len(p)
    if sira is None or not dizi[sira]:
        return False
    sol = sira
    while sol > 0 and dizi[sol - 1]:
        sol -= 1
    sag = sira
    while sag + 1 < len(dizi) and dizi[sag + 1]:
        sag += 1
    return sag - sol + 1 >= 3


def kesmeli_adlar(bloklar: list[Blok]) -> Counter:
    """Kitapta kesmeyle yazılmış özel adlar: "Tibet’e" → Tibet."""
    return Counter(m.group(1) for b in bloklar for m in _KESMELI.finditer(b.metin))


def kesme_denetimi(blok: Blok, kesmeli: Counter, cozumle: Cozumleyici | None = None) -> list[Tespit]:
    """kesmeli: kitapta kesmeyle yazılmış özel adlar (kesmeli_adlar)."""
    cozumle = cozumle or zemberek_analizleri
    metin = blok.metin
    tespitler = []
    for m in _KELIME.finditer(metin):
        if _SONRAKI_AD.match(metin, m.end()) or eser_listesinde(metin, m.start()):
            continue  # çok kelimeli adın içi (ek son kelimeye gelir) ya da eser adları listesi
        dogru = ozel_ad_eki(m.group(0), cozumle)
        if not dogru:
            continue
        ad = dogru.split("'")[0]
        sayi = kesmeli[ad] + (kesmeli[ad[:-1] + _SERT[ad[-1]]] if ad[-1] in _SERT else 0)
        if sayi:
            tespitler.append(_tespit(blok, "ozel_ad_kesme", m.group(0),
                                     f"Özel ada gelen ek kesmeyle ayrılır: '{dogru}' (TDK). Kitap bu adı "
                                     f"başka yerde {sayi} kez kesmeyle yazmış."))
    for m in _KISALTMA_EKI.finditer(metin):
        tespitler.append(_tespit(blok, "kisaltma_kesme", m.group(0),
                                 f"Kısaltmaya gelen ek kesmeyle ayrılır: '{m.group(1)}'{m.group(2)}' (TDK)."))
    for m in _SAYI_EKI.finditer(metin):
        tespitler.append(_tespit(blok, "sayi_kesme", m.group(0),
                                 f"Sayıya gelen ek kesmeyle ayrılır: '{m.group(1)}'{m.group(2)}' (TDK)."))
    for m in _KESMELI.finditer(metin):
        sebep = gereksiz_kesme(m.group(1), m.group(2), cozumle)
        if sebep:
            tespitler.append(_tespit(blok, "gereksiz_kesme", m.group(0),
                                     f"Kesme gereksiz: '{m.group(1)}{m.group(2)}' yazılır ({sebep}, TDK)."))
    return tespitler
