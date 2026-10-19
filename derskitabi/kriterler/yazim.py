"""Yazım ve dil kriteri (Faz 1, adım 3).

Girdi : Blok listesi ("paragraf" ve "kisa" türleri; K8)
Çıktı : Tespit listesi (kriter="yazim")

İki parça:
  1. Kelime denetimi (K13): her kelime iki morfolojik çözümleyiciye sorulur —
     Starlang (ana denetçi) ve Zemberek (ikinci görüş). İkisi de çözümleyemezse
     güven 1,0; yalnız biri çözümleyemezse 0,5.
  2. TDK kuralları (K14): R1 noktalamadan sonra boşluk, R3–R5 ayrı yazılan de/da ve
     mi, R6 yada, R7 bitişik/ayrı yazım listesi, R8 bağlaç tekrarı.

Kullanım:
    python -m derskitabi.kriterler.yazim veri/kitap_bloklar.json
"""

import argparse
import functools
import logging
import re
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from ..kayit import bloklari_yukle, tespitleri_kaydet
from ..model import Blok, Tespit

# Bir kelimenin geçerli olup olmadığını söyleyen fonksiyon (kelime -> bool)
Denetci = Callable[[str], bool]

_HARF = r"A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû"
_KUCUK = r"a-zçğıöşüâîû"
_KELIME = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
_WEB = re.compile(r"\S*(?:www\.|https?://|@|\.(?:com|gov|edu|org|net|tr)\b)\S*", re.I)
KISALTMALAR = {"s", "vb", "vs", "bk", "bkz", "örn", "yy", "sf", "no", "dr", "prof", "doç", "hz",
               "çev", "haz", "ed", "bs", "c", "m.ö", "m.s",
               "km", "cm", "mm", "m", "kg", "g", "ha", "lt", "sn", "dk"}
# Büyük harfle başlayan kelimeler denetlensin mi? Kitapta bunların neredeyse tamamı özel isim
# (harita etiketleri: Onega, Bakırçay, NAHÇIVAN…) çıktı; araçlar özel isimleri bilmediği için
# sahte hata üretiyorlar. Faz 1'de denetlenmez, sayıları raporlanır (bkz. F3: LLM hakemi).
BUYUK_HARF_DENETIMI = False
KALIN_UNLULER = set("aıouâû")
UNLULER = set("aeıioöuüâîû")
_SORU_UYUMU = {"a": "ı", "ı": "ı", "â": "ı", "e": "i", "i": "i", "î": "i",
               "o": "u", "u": "u", "û": "u", "ö": "ü", "ü": "ü"}
_SORU_EKI = re.compile(r"m([ıiuü])(y?[ıiuü]m|s[ıiuü]n|y[ıiuü]z|s[ıiuü]n[ıiuü]z|d[ıiuü]r|"
                       r"yd[ıiuü]|ym[ıiuü]ş|yken|yd[ıiuü][mnk]|ys[ae])?")

# R7: (yanlış yazım, doğru yazım)
BITISIK_AYRI = [("hiç bir", "hiçbir"), ("bir çok", "birçok"), ("bir kaç", "birkaç"),
                ("her hangi", "herhangi"), ("hiç biri", "hiçbiri"), ("birden bire", "birdenbire"),
                ("birşey", "bir şey"), ("herşey", "her şey"), ("hiçkimse", "hiç kimse"),
                ("herbiri", "her biri"), ("birgün", "bir gün"), ("hergün", "her gün")]
TEKRAR_EDILMEYEN = {"ve", "ile", "veya", "ya", "ama", "fakat", "için", "da", "de"}
# Sondan ayrılınca geçerli kelime kalıyorsa "ayrı yazılmalı olabilir" notu eklenen ekler
_AYRILABILIR_EKLER = ["mısın", "misin", "musun", "müsün", "mıyım", "miyim", "muyum", "müyüm",
                      "mıdır", "midir", "mudur", "müdür", "mı", "mi", "mu", "mü", "ki", "de", "da"]


def tr_kucuk(k: str) -> str:
    """Türkçeye uygun küçük harf: I -> ı, İ -> i (Python'un lower() bunları yanlış çevirir)."""
    return k.replace("I", "ı").replace("İ", "i").lower()


def son_unlu(k: str) -> str | None:
    return next((c for c in reversed(k.lower()) if c in UNLULER), None)


# --- 1. Kelime denetimi ---

@functools.cache
def varsayilan_denetciler() -> tuple[Denetci, Denetci]:
    """(Starlang, Zemberek) denetçileri. Yüklemesi birkaç saniye sürdüğü için bir kez kurulur."""
    logging.getLogger("zemberek").setLevel(logging.ERROR)
    from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
    from zemberek import TurkishMorphology

    starlang = FsmMorphologicalAnalyzer()
    zemberek = TurkishMorphology.create_with_defaults()
    return (functools.cache(lambda k: starlang.morphologicalAnalysis(k).size() > 0),
            functools.cache(lambda k: len(zemberek.analyze(k).analysis_results) > 0))


def _gecerli(denetci: Denetci, kelime: str) -> bool:
    """Kelime ya da Türkçe küçük harfli hâli geçerliyse True. Büyük harfli başlıklarda
    PDF'in "İ"yi "I" olarak kaydettiği görüldü (s.7), o yüzden I->İ biçimi de denenir."""
    adaylar = [kelime, tr_kucuk(kelime)]
    if "I" in kelime:
        adaylar.append(tr_kucuk(kelime.replace("I", "İ")))
    try:
        return any(denetci(a) for a in dict.fromkeys(adaylar))
    except Exception:  # noqa: BLE001 — araç bu kelimede çökerse "bilinmiyor" say, hata üretme
        return True


def _cumle_basi_mi(metin: str, bas: int) -> bool:
    onceki = metin[:bas].rstrip(" \"'“‘(«")
    return not onceki or onceki[-1] in ".!?:…"


def _aralikli_mi(metin: str) -> bool:
    """Harfleri aralıklı yazılmış harita etiketi ("YU N A N İ S TA N")."""
    kelimeler = metin.split()
    return len(kelimeler) >= 4 and sum(map(len, kelimeler)) / len(kelimeler) < 2.5


def _atlanma_sebebi(metin: str, m: re.Match, ilk: bool, son: bool) -> str | None:
    """Geçersiz bulunan kelime, sahte hata olma ihtimali yüksek bir türdense sebebi döner."""
    kelime = m.group(0)
    sade = kelime.replace("’", "'")
    if len(kelime) <= 3:
        return "çok kısa (bölünmüş kelime parçası olabilir)"
    if not sade.replace("'", "").isalpha():
        return "rakam / sembol içeriyor (km²'lik gibi)"
    if sade.lower() in KISALTMALAR or sade.split("'")[0].lower() in KISALTMALAR:
        return "kısaltma / ölçü birimi"
    if kelime.isupper() and len(kelime) <= 5:
        return "büyük harfli kısaltma"
    if "'" in sade and sade.split("'")[0][:1].isupper():
        return "özel isim + ek"
    if kelime[0].isupper() and not BUYUK_HARF_DENETIMI:
        return "büyük harfle başlıyor (özel isim / başlık olabilir)"
    if kelime[0].isupper() and not kelime.isupper() and not _cumle_basi_mi(metin, m.start()):
        return "cümle ortasında büyük harf (özel isim)"
    if ilk and kelime[0].islower():
        return "blok başında küçük harf (önceki bloktan bölünmüş kelime olabilir)"
    if metin[m.end():m.end() + 1] in "-‐":
        return "satır sonunda bölünmüş kelime"
    if son and not metin[m.end():].strip():
        return "blok sonunda noktalamasız (sonraki bloğa bölünmüş kelime olabilir)"
    return None


def _ek_notu(kelime: str, denetci: Denetci) -> str:
    k = tr_kucuk(kelime)
    for ek in _AYRILABILIR_EKLER:
        if k.endswith(ek) and len(k) > len(ek) + 2 and _gecerli(denetci, k[:-len(ek)]):
            tur = "soru eki" if ek.startswith("m") else ("bağlaç 'ki'" if ek == "ki" else "bağlaç 'de/da'")
            return f" Sondaki '{ek}' ayrılınca geçerli bir kelime kalıyor: {tur} ayrı yazılmalı olabilir ('{k[:-len(ek)]} {ek}')."
    return ""


def kelime_denetimi(blok: Blok, denetciler: tuple[Denetci, Denetci],
                    atlananlar: Counter | None = None) -> list[Tespit]:
    starlang, zemberek = denetciler
    metin = _WEB.sub(lambda w: " " * len(w.group(0)), blok.metin)  # konumlar korunur
    if _aralikli_mi(metin):
        return []
    tespitler = []
    eslesmeler = list(_KELIME.finditer(metin))
    for i, m in enumerate(eslesmeler):
        kelime = m.group(0)
        st_gecerli = _gecerli(starlang, kelime)
        zb_gecerli = _gecerli(zemberek, kelime)
        if st_gecerli and zb_gecerli:
            continue
        sebep = _atlanma_sebebi(metin, m, ilk=(i == 0), son=(i == len(eslesmeler) - 1))
        if sebep:
            if atlananlar is not None:
                atlananlar[sebep] += 1
            continue
        hemfikir = not st_gecerli and not zb_gecerli
        kim = "iki araç da (Starlang ve Zemberek)" if hemfikir else (
            "yalnız Starlang" if not st_gecerli else "yalnız Zemberek")
        tespitler.append(_tespit(
            blok, "morfoloji", 1.0 if hemfikir else 0.5, kelime,
            f"'{kelime}' kelimesi Türkçe kök ve ek kurallarına göre çözümlenemedi ({kim}); "
            f"yazım hatası olabilir." + _ek_notu(kelime, starlang)))
    return tespitler


# --- 2. TDK kuralları ---

def _tespit(blok: Blok, alt_tur: str, guven: float, parca: str, aciklama: str) -> Tespit:
    return Tespit(sayfa_no=blok.sayfa_no, blok_no=blok.blok_no, bbox=blok.bbox, kriter="yazim",
                  aciklama=aciklama, guven_skoru=guven, basili_sayfa_no=blok.basili_sayfa_no,
                  alt_tur=alt_tur, metin_parcasi=parca)


def kural_denetimi(blok: Blok) -> list[Tespit]:
    metin = _WEB.sub(lambda w: " " * len(w.group(0)), blok.metin)
    tespitler = []

    # R1: noktalamadan sonra boşluk yok
    for m in re.finditer(rf"(\S*?[{_KUCUK}])([.,;:!?])(?=[{_HARF}]|\(…\)|\(\.\.\.\))", metin):
        onceki_kelime = re.split(r"[^\w]", m.group(1))[-1].lower()
        sonraki = metin[m.end():m.end() + 15].split()[0] if metin[m.end():].strip() else ""
        if (onceki_kelime in KISALTMALAR or len(onceki_kelime) <= 1
                or any(c.isdigit() for c in m.group(1) + sonraki)):
            continue  # kısaltma, "x,y" gibi değişken, formül/birim
        ucnokta = metin[m.end():].startswith(("(…", "(..."))
        parca = metin[max(0, m.start(2) - 12):m.end(2) + 12].strip()
        tespitler.append(_tespit(
            blok, "noktalama_bosluk", 0.5 if ucnokta else 1.0, parca,
            f"'{m.group(2)}' işaretinden sonra boşluk bırakılmamış." +
            (" Alıntıdaki (…) işaretinden önce de boşluk bırakılır; tasarım tercihi de olabilir."
             if ucnokta else "")))

    # R6: "ya da" bitişik yazılmış
    for m in re.finditer(rf"(?<![{_HARF}])[Yy]ada(?![{_HARF}])", metin):
        tespitler.append(_tespit(blok, "ya_da", 1.0, m.group(0),
                                 "'ya da' bağlacı ayrı yazılır ('yada' değil)."))

    # R7: bitişik / ayrı yazım listesi
    for yanlis, dogru in BITISIK_AYRI:
        for m in re.finditer(rf"(?<![{_HARF}]){yanlis}(?![{_HARF}])", metin, re.I):
            tespitler.append(_tespit(blok, "bitisik_ayri", 1.0, m.group(0),
                                     f"'{m.group(0)}' değil, '{dogru}' yazılır (TDK)."))

    if blok.tur != "paragraf" or _aralikli_mi(metin):
        return tespitler

    kelimeler = list(re.finditer(rf"[{_HARF}0-9’'.]+", metin))
    for once_m, simdi_m in zip(kelimeler, kelimeler[1:]):
        once, simdi = once_m.group(0), simdi_m.group(0).lower().rstrip(".,;:!?")
        if (any(c.isdigit() for c in once) or once.lower().rstrip(".") in KISALTMALAR
                or once.isupper() or simdi_m.group(0).isupper()):
            continue  # büyük harfli metin: harita etiketi/başlık ("KIY DA", "ER TA")
        ou = son_unlu(once)
        parca = f"{once} {simdi_m.group(0)}"
        # R3: bağlaç de/da "te/ta" yazılmış
        if simdi in ("te", "ta"):
            tespitler.append(_tespit(blok, "bag_te_ta", 1.0, parca,
                                     "Bağlaç olan 'de/da' her zaman 'd' ile yazılır; 'te/ta' yazılmaz."))
        # R4: ayrı yazılan de/da'da ünlü uyumu
        elif simdi in ("de", "da") and ou:
            beklenen = "da" if ou in KALIN_UNLULER else "de"
            if simdi != beklenen:
                tespitler.append(_tespit(blok, "bag_de_da_uyum", 1.0, parca,
                                         f"Bağlaç ünlü uyumuna uyar: '{once} {beklenen}' olmalı."))
        # R5: ayrı yazılan soru eki mi'de ünlü uyumu
        elif (sm := _SORU_EKI.fullmatch(simdi)) and ou and sm.group(1) != _SORU_UYUMU[ou]:
            dogru = "m" + _SORU_UYUMU[ou] + simdi[2:]
            tespitler.append(_tespit(blok, "soru_eki_uyum", 1.0, parca,
                                     f"Soru eki ünlü uyumuna uyar: '{once} {dogru}' olmalı."))
        # R8: bağlaç tekrarı
        if simdi == once.lower() and simdi in TEKRAR_EDILMEYEN:
            tespitler.append(_tespit(blok, "kelime_tekrari", 1.0, parca,
                                     f"'{simdi}' art arda iki kez yazılmış."))
    return tespitler


def analiz_et(bloklar: list[Blok], denetciler: tuple[Denetci, Denetci] | None = None,
              atlananlar: Counter | None = None) -> list[Tespit]:
    """Paragraf ve kısa metin bloklarında yazım tespitleri (bozuk ve simge bloklar atlanır, K8)."""
    if denetciler is None:
        denetciler = varsayilan_denetciler()
    tespitler = []
    for b in bloklar:
        if b.tur in ("paragraf", "kisa"):
            tespitler += kelime_denetimi(b, denetciler, atlananlar)
            tespitler += kural_denetimi(b)
    return tespitler


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Yazım ve dil kriteri")
    ap.add_argument("bloklar_json", type=Path)
    arg = ap.parse_args()

    atlananlar = Counter()
    tespitler = analiz_et(bloklari_yukle(arg.bloklar_json), atlananlar=atlananlar)
    kok = arg.bloklar_json.with_name(arg.bloklar_json.stem.removesuffix("_bloklar"))
    tespitleri_kaydet(tespitler, f"{kok}_yazim_tespitler.json")

    print(f"{len(tespitler)} yazım tespiti (güven 1,0: {sum(t.guven_skoru == 1.0 for t in tespitler)})")
    for tur, n in Counter(t.alt_tur for t in tespitler).most_common():
        print(f"  {tur}: {n}")
    print("Atlanan (sahte hata önlemi): " + ", ".join(f"{s} {n}" for s, n in atlananlar.most_common()))


if __name__ == "__main__":
    main()
