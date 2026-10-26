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

from dataclasses import replace

from ..kayit import bloklari_yukle, tespitleri_kaydet
from ..model import Blok, Tespit
from ..satirlar import grup_metni, satir_gruplari

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
# Kitapta bu kadar ve daha fazla kez geçen "geçersiz" kelime, araçların bilmediği ama kitabın
# tutarlı kullandığı bir terim sayılır (Matematik 11: "trigonometrik" 141 kez). Gerçek yazım
# hataları kitapta genellikle 1–2 kez geçiyor. Atlanan terimler ayrıca raporlanır.
TERIM_TEKRAR_ESIGI = 3
# Bir blokta (en az BLOK_MIN_KELIME kelime) kelimelerin bu oranından fazlası iki araca göre de
# geçersizse, sorun kitapta değil PDF okumada olabilir (ör. İstiklal Marşı sayfasında "ı"
# harfleri hiç kaydedilmemiş: "altndaki"). Böyle bir blokta kelime tespiti üretilmez.
OKUMA_SORUNU_ORANI = 0.3
BLOK_MIN_KELIME = 6
# Fontun bir harfi hiç kaydetmediği bloklar (Matematik 11, İstiklal Marşı: "altndaki",
# "vuracakm"): geçersiz kelimeye tek bir "ı"/"i" eklenince geçerli oluyorsa harf düşmüş
# demektir. Bir blokta bu kadar kelimede görülürse blok "PDF okuma sorunu" sayılır.
DUSMUS_HARF_ESIGI = 3
_MATEMATIK = re.compile(r"(?:arc)?(?:sin|cos|tan|cot|sec|csc|log|ln|lim)[a-zθαβ]{0,2}", re.I)
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

class _TanimSirasiylaKume(set):
    """Kök özelliklerini (RootAttribute) tanım sırasıyla dolaşan küme."""

    def __iter__(self):
        return iter(sorted(set.__iter__(self), key=lambda a: a.value))


def zemberek_kok_sirasini_sabitle() -> None:
    """zemberek-python'daki bir sıra hatasını giderir (K26 eki).

    Kökün özellikleri bir kümeden okunup sırayla uygulanıyor; kümenin sırası Python'un her
    çalıştırmada değişen hash tohumuna bağlı. "tıp" kökünde yumuşama (p→b) ikizleşmeden (b→bb)
    önce gelirse "tıbb-" doğru üretiliyor, sonra gelirse "tıpb-" çıkıyor ve "tıbba", "tıbbın"
    bazı çalıştırmalarda geçersiz sayılıyordu (aynı kitap 77 ya da 78 tespit veriyordu).
    Java'daki asıl Zemberek özellikleri tanım sırasıyla uygular; burada da öyle yapılır.
    Paketin dosyasına dokunulmaz (yeniden kurulumda kaybolmasın)."""
    from zemberek.morphology.morphotactics.turkish_morphotactics import StemTransitionsBase
    if getattr(StemTransitionsBase, "_sira_sabit", False):
        return
    asil = StemTransitionsBase.generate_modified_root_nodes

    def tanim_sirasiyla(self, dic_item):
        eski = dic_item.attributes
        dic_item.attributes = _TanimSirasiylaKume(eski)
        try:
            return asil(self, dic_item)
        finally:
            dic_item.attributes = eski

    StemTransitionsBase.generate_modified_root_nodes = tanim_sirasiyla
    StemTransitionsBase._sira_sabit = True


@functools.cache
def starlang_cozumleyici():
    """Starlang biçimbilim çözümleyicisi (bir kez yüklenir; alıntı ayırma da özel adlar için kullanır)."""
    from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
    return FsmMorphologicalAnalyzer()


@functools.cache
def varsayilan_denetciler() -> tuple[Denetci, Denetci]:
    """(Starlang, Zemberek) denetçileri. Yüklemesi birkaç saniye sürdüğü için bir kez kurulur."""
    logging.getLogger("zemberek").setLevel(logging.ERROR)
    from zemberek import TurkishMorphology

    zemberek_kok_sirasini_sabitle()  # TurkishMorphology kurulmadan önce
    starlang = starlang_cozumleyici()
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


def _harf_dusmus_mu(kelime: str, denetciler: tuple[Denetci, Denetci]) -> bool:
    """Kelimeye bir 'ı' ya da 'i' eklenince iki araca göre de geçerli oluyor mu?"""
    k = tr_kucuk(kelime)
    for i in range(1, len(k) + 1):
        for harf in "ıi":
            aday = k[:i] + harf + k[i:]
            if all(_gecerli(d, aday) for d in denetciler):
                return True
    return False


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
    if _MATEMATIK.fullmatch(kelime):
        return "matematik gösterimi (sinx, cotx)"
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
                    atlananlar: Counter | None = None, iz: dict | None = None) -> list[Tespit]:
    """iz verilirse, her kelime için araçların kararı ve atlanma sebebi buraya yazılır
    (inceleyici bunu "adım adım" gösterir; karar mantığı yalnız burada durur)."""
    starlang, zemberek = denetciler
    metin = _WEB.sub(lambda w: " " * len(w.group(0)), blok.metin)  # konumlar korunur
    if iz is None:
        iz = {}
    iz.update(blok_durumu="denetlendi", kelimeler=[])
    if _aralikli_mi(metin):
        iz["blok_durumu"] = "aralikli"
        return []
    tespitler = []
    eslesmeler = list(_KELIME.finditer(metin))
    sonuclar = [(_gecerli(starlang, m.group(0)), _gecerli(zemberek, m.group(0))) for m in eslesmeler]
    iz["kelimeler"] = [{"kelime": m.group(0), "starlang": st, "zemberek": zb, "sebep": None}
                       for m, (st, zb) in zip(eslesmeler, sonuclar)]
    # Oran yalnız 4+ harfli kelimelerle hesaplanır: formüllerdeki tek harfli değişkenler
    # ("x", "k", "R") okuma sorunu sayılmasın
    uzunlar = [(st, zb) for m, (st, zb) in zip(eslesmeler, sonuclar) if len(m.group(0)) >= 4]
    ikisi_gecersiz = sum(1 for st, zb in uzunlar if not st and not zb)
    iz.update(uzun_kelime=len(uzunlar), ikisi_gecersiz=ikisi_gecersiz)
    if len(uzunlar) >= BLOK_MIN_KELIME and ikisi_gecersiz / len(uzunlar) > OKUMA_SORUNU_ORANI:
        iz["blok_durumu"] = "okuma_orani"
        if atlananlar is not None:
            atlananlar["PDF okuma sorunu şüphesi (blok)"] += 1
        return []
    dusmus = sum(1 for m, (st, zb) in zip(eslesmeler, sonuclar)
                 if not st and not zb and len(m.group(0)) >= 4 and m.group(0).islower()
                 and _harf_dusmus_mu(m.group(0), denetciler))
    iz["dusmus_harf"] = dusmus
    if dusmus >= DUSMUS_HARF_ESIGI:
        iz["blok_durumu"] = "dusmus_harf"
        if atlananlar is not None:
            atlananlar["PDF okuma sorunu: harf düşmüş (blok)"] += 1
        return []
    for i, (m, (st_gecerli, zb_gecerli)) in enumerate(zip(eslesmeler, sonuclar)):
        kelime = m.group(0)
        if st_gecerli and zb_gecerli:
            continue
        sebep = _atlanma_sebebi(metin, m, ilk=(i == 0), son=(i == len(eslesmeler) - 1))
        iz["kelimeler"][i]["sebep"] = sebep
        if sebep:
            if atlananlar is not None:
                atlananlar[sebep] += 1
            continue
        hemfikir = not st_gecerli and not zb_gecerli
        kim = "iki araç da: Starlang ve Zemberek" if hemfikir else (
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
        # Güven 0,5: "yada" nadiren "yâd" (yabancı) kelimesinin yönelme hâli olabilir
        # ("söyleme yada" — bir türküde görüldü)
        tespitler.append(_tespit(blok, "ya_da", 0.5, m.group(0),
                                 "'ya da' bağlacı ayrı yazılır ('yada' değil). Edebî metinde "
                                 "'yâda' (yabancıya) anlamında olabilir."))

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
        sonraki_karakter = metin[simdi_m.end():simdi_m.end() + 1]
        # R3: bağlaç de/da "te/ta" yazılmış. "ta" aynı zamanda zarftır ("ta Uşak'tan geldik",
        # "ta eskiden" — Türk Dili ve Edebiyatı 9'da görüldü); bu yüzden "ta" yalnız
        # noktalamadan hemen önceyse ("kitap ta,") bağlaç sayılır.
        if simdi == "te" or (simdi == "ta" and sonraki_karakter in ",.;:!?"):
            tespitler.append(_tespit(blok, "bag_te_ta", 1.0, parca,
                                     "Bağlaç olan 'de/da' her zaman 'd' ile yazılır; 'te/ta' yazılmaz."))
        # R4: ayrı yazılan de/da'da ünlü uyumu
        elif simdi in ("de", "da") and ou:
            beklenen = "da" if ou in KALIN_UNLULER else "de"
            if simdi != beklenen:
                tespitler.append(_tespit(blok, "bag_de_da_uyum", 1.0, parca,
                                         f"Bağlaç ünlü uyumuna uyar: '{once} {beklenen}' olmalı."))
        # R5: ayrı yazılan soru eki mi'de ünlü uyumu
        elif ((sm := _SORU_EKI.fullmatch(simdi)) and ou and sm.group(1) != _SORU_UYUMU[ou]
              and sonraki_karakter not in "-‐"):  # "mü-" satır sonunda bölünmüş kelime
            dogru = "m" + _SORU_UYUMU[ou] + simdi[2:]
            tespitler.append(_tespit(blok, "soru_eki_uyum", 1.0, parca,
                                     f"Soru eki ünlü uyumuna uyar: '{once} {dogru}' olmalı."))
        # R8: bağlaç tekrarı
        if simdi == once.lower() and simdi in TEKRAR_EDILMEYEN:
            tespitler.append(_tespit(blok, "kelime_tekrari", 1.0, parca,
                                     f"'{simdi}' art arda iki kez yazılmış."))
    return tespitler


def kitap_kelime_sayilari(bloklar: list[Blok]) -> Counter:
    """Her kelimenin (Türkçe küçük harfle) kitapta kaç kez geçtiği."""
    return Counter(map(tr_kucuk, (k for b in bloklar for k in _KELIME.findall(b.metin))))


def kitaba_ozel_terimler(adaylar: set[str], kitap_kelimeleri: Counter,
                         starlang: Denetci) -> dict[str, str]:
    """Araçların tanımadığı ama kitapta sık tekrar eden kelimeler (K15): {kelime: terim kökü}.

    Terimin ek almış hâlleri (Biyoloji 10: villus ×9 → villusları, villuslardaki…): kelime,
    kitapta kendisi terim olan (tek başına ≥ eşik kez geçen, araçların tanımadığı) bir
    kökle başlıyorsa terim sayılır. Kökün *tek başına* sık geçmesi şartı, sık tekrarlanmayan
    bir yazım hatasının ("foksiyon" → "foksiyonun") ek almış hâllerinin terime
    dönüşmesini engeller.
    """
    terimler = {}
    for aday in adaylar:
        kok = next((aday[:i] for i in range(len(aday), 4, -1)
                    if kitap_kelimeleri[aday[:i]] >= TERIM_TEKRAR_ESIGI
                    and (i == len(aday) or not _gecerli(starlang, aday[:i]))), None)
        if kok:
            terimler[aday] = kok
    return terimler


def birlesik_paragraf(grup: list[Blok], denetciler) -> Blok:
    """Satır satır bloklara bölünmüş paragraf tek blok olarak denetlenir (satirlar.py). Tek blok
    denetlenince her satırın ilk ve son kelimesi "bölünmüş parça olabilir" diye atlanıyordu (TDE 12'de
    metnin çoğu satır blokları). Tiresi kaybolmuş kelimeler ("Ga" + "rip") birleştirilir."""
    from ..pdf_cikarma import blok_turu
    metin, _ = grup_metni(grup, bilesik_mi=lambda k: any(_gecerli(d, k) for d in denetciler),
                          parca_mi=lambda k: all(_gecerli(d, k) for d in denetciler))
    kutu = (min(x.bbox[0] for x in grup), min(x.bbox[1] for x in grup),
            max(x.bbox[2] for x in grup), max(x.bbox[3] for x in grup))
    return Blok(grup[0].sayfa_no, grup[0].blok_no, kutu, metin, grup[0].basili_sayfa_no, blok_turu(metin))


def satira_bagla(tespitler: list[Tespit], grup: list[Blok], metin: str) -> list[Tespit]:
    """Birleşik paragraftaki tespiti kelimenin bulunduğu satır bloğuna geri bağlar (blok numaraları
    değişmesin: test setleri ve notlar bloğa göre)."""
    if len(grup) == 1:
        return tespitler
    baslar = [metin.find(x.metin.strip()[:20]) for x in grup]
    sonuc = []
    for t in tespitler:
        yer = metin.find(t.metin_parcasi or "")
        i = max((j for j, bas in enumerate(baslar) if 0 <= bas <= yer), default=0)
        sonuc.append(replace(t, blok_no=grup[i].blok_no, bbox=grup[i].bbox))
    return sonuc


def analiz_et(bloklar: list[Blok], denetciler: tuple[Denetci, Denetci] | None = None,
              atlananlar: Counter | None = None,
              kitap_bloklari: list[Blok] | None = None) -> list[Tespit]:
    """Paragraf ve kısa metin bloklarında yazım tespitleri (bozuk ve simge bloklar atlanır, K8).

    kitap_bloklari: yalnız bazı sayfalar denetlenirken kitabın tamamı; "kitaba özel terim"
    sayımı (K15) her zaman tüm kitaba göre yapılır. Verilmezse bloklar kullanılır.
    """
    if denetciler is None:
        denetciler = varsayilan_denetciler()
    kelime_tespitleri, kural_tespitleri = [], []
    for grup in satir_gruplari(bloklar):
        b = grup[0] if len(grup) == 1 else birlesik_paragraf(grup, denetciler)
        if b.tur in ("paragraf", "kisa"):
            kelime_tespitleri += satira_bagla(kelime_denetimi(b, denetciler, atlananlar), grup, b.metin)
            kural_tespitleri += satira_bagla(kural_denetimi(b), grup, b.metin)

    kitap_kelimeleri = kitap_kelime_sayilari(kitap_bloklari or bloklar)
    terimler = kitaba_ozel_terimler({tr_kucuk(t.metin_parcasi) for t in kelime_tespitleri},
                                    kitap_kelimeleri, denetciler[0])
    if atlananlar is not None:
        for kok in terimler.values():
            atlananlar[f"kitaba özel terim (≥{TERIM_TEKRAR_ESIGI} kez)"] += 1
            atlananlar[f"terim: {kok}"] = kitap_kelimeleri[kok]

    # Düşmüş harf (K15) sayfa düzeyinde de sayılır: İstiklal Marşı'nda her dize ayrı bir
    # blok olabildiği için blok düzeyindeki eşik tek başına yetmiyor (Biyoloji 10).
    kalan = [t for t in kelime_tespitleri if tr_kucuk(t.metin_parcasi) not in terimler]
    dusmus = [t for t in kalan if t.metin_parcasi.islower() and _harf_dusmus_mu(t.metin_parcasi, denetciler)]
    sayfa_dusmus = Counter(t.sayfa_no for t in dusmus)
    okuma_sorunlu = {id(t) for t in dusmus if sayfa_dusmus[t.sayfa_no] >= DUSMUS_HARF_ESIGI}
    if atlananlar is not None and okuma_sorunlu:
        atlananlar["PDF okuma sorunu: harf düşmüş (sayfa)"] += len(okuma_sorunlu)
    return [t for t in kalan if id(t) not in okuma_sorunlu] + kural_tespitleri


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Yazım ve dil kriteri")
    ap.add_argument("bloklar_json", type=Path)
    ap.add_argument("--hakem", action="store_true",
                    help="Kelime tespitlerini yerel dil modeline danış (K25; Ollama gerekir)")
    arg = ap.parse_args()

    atlananlar = Counter()
    bloklar = bloklari_yukle(arg.bloklar_json)
    tespitler = analiz_et(bloklar, atlananlar=atlananlar)
    kok = arg.bloklar_json.with_name(arg.bloklar_json.stem.removesuffix("_bloklar"))
    pdf = Path(f"{kok}.pdf")
    if pdf.exists():  # kitap ipuçları (K28 alıntı, K29 PDF parçası ve terim): yazı biçimleri PDF'ten okunur
        from . import dusuk_oncelik
        tespitler = dusuk_oncelik.isaretle(pdf, bloklar, tespitler)
        ipucu = Counter(filter(None, map(dusuk_oncelik.sebep, tespitler)))
        print("Düşük önceliğe inen kelime tespitleri: " + (", ".join(f"{a} {n}" for a, n in ipucu.most_common()) or "yok"))
    if arg.hakem:
        import json
        from .yazim_hakem import hakemle
        onbellek_yolu = arg.bloklar_json.with_name("yazim_hakem_onbellek.json")
        onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
        try:
            tespitler = hakemle(tespitler, bloklar, onbellek=onbellek, ilerleme=print)
        finally:
            onbellek_yolu.write_text(json.dumps(onbellek, ensure_ascii=False), encoding="utf-8")
    tespitleri_kaydet(tespitler, f"{kok}_yazim_tespitler.json")

    print(f"{len(tespitler)} yazım tespiti (güven 1,0: {sum(t.guven_skoru == 1.0 for t in tespitler)})")
    for tur, n in Counter(t.alt_tur for t in tespitler).most_common():
        print(f"  {tur}: {n}")
    terimler = {s[7:]: n for s, n in atlananlar.items() if s.startswith("terim: ")}
    print("Atlanan (sahte hata önlemi): " + ", ".join(
        f"{s} {n}" for s, n in atlananlar.most_common() if not s.startswith("terim: ")))
    if terimler:
        print("Kitaba özel terimler (araçlar tanımıyor, kitapta tekrar ediyor): " + ", ".join(
            f"{k}×{n}" for k, n in sorted(terimler.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
