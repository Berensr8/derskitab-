"""Sonuç ekranının içeriği: her kriter için basit cümleler, örnek alıntılar ve tek tek inceleme listesi.

Cümleler burada kurulur (ekran yalnız gösterir), böylece test edilebilir ve Excel/PDF'teki
öncelik kuralıyla aynıdır: yüksek (güven ≥ 0,75) "önce bakın", orta (≥ 0,5) "kontrol edin",
düşük (< 0,5) "düşük öncelik" (terim, alıntı, PDF okuma sorunu ya da hakemin "muhtemelen doğru"su).
"""

import re
from collections import Counter

from ..model import Blok, Tespit
from ..pdf_notlari import oncelik
from ..rapor import TUR_ADLARI

KRITERLER = {"yazim": "Yazım ve dil", "okunabilirlik": "Dilsel karmaşıklık",
             "mufredat": "Müfredat kavramları", "tutarlilik": "Bilgi tutarsızlığı"}
ORNEK_SAYISI = 3
_SADE_TUR = {"morfoloji": "kelime yazımı", "kitap_ici_zor_paragraf": "zor paragraf"}


def tur_adi(alt_tur: str | None) -> str:
    ad = _SADE_TUR.get(alt_tur) or TUR_ADLARI.get(alt_tur or "", alt_tur or "diğer")
    return ad.removeprefix("TDK kuralı: ")


def _alinti(metin: str, parca: str | None, pay: int = 70) -> dict:
    """Blok metninden parçanın çevresi: {"once", "vurgu", "sonra"} (ekranda vurgu kırmızı altı çizili)."""
    metin = " ".join(metin.split())
    i = metin.find(parca) if parca else -1
    if i < 0:
        kisa = metin[:2 * pay]
        if len(metin) > len(kisa) and " " in kisa:
            kisa = kisa[:kisa.rfind(" ")].rstrip(",;:")  # kelime ortasından kesme
        return {"once": "", "vurgu": "", "sonra": kisa + ("…" if len(metin) > len(kisa) else "")}
    bas, son = max(0, i - pay), min(len(metin), i + len(parca) + pay)
    # kelime ortasından kesme
    while 0 < bas < i and metin[bas - 1] != " ":
        bas += 1
    while i + len(parca) < son < len(metin) and metin[son] != " ":
        son -= 1
    return {"once": ("…" if bas > 0 else "") + metin[bas:i], "vurgu": parca,
            "sonra": metin[i + len(parca):max(son, i + len(parca))] + ("…" if son < len(metin) else "")}


def kisa_aciklama(t: Tespit) -> str:
    """Listede görünen tek cümle; tam açıklama ayrıntıda."""
    if t.kriter == "yazim" and t.alt_tur == "morfoloji":
        oneri = re.search(r"Önerilen yazım: '([^']+)'", t.aciklama)
        return "Sözlükte bulunamadı, yanlış yazılmış olabilir" + (f" (önerilen: {oneri.group(1)})" if oneri else "") + "."
    if t.kriter == "tutarlilik":
        return t.aciklama.split(" çelişiyor olabilir")[0] + " çelişiyor olabilir."
    if t.kriter == "okunabilirlik":
        m = re.match(r"(Bu paragraf[^.]*\.)", t.aciklama)
        return m.group(1) if m else t.aciklama.split(". ")[0] + "."
    if t.kriter == "mufredat":
        if t.alt_tur == "tema_yok":
            return "Bu temanın anahtar kavramlarının çoğu kitapta geçmiyor; tema başka bir ciltte olabilir."
        if "tanıtım" in t.aciklama:
            return "Yalnız tanıtım ya da kapak sayfasında geçiyor, konu anlatımında yok."
        return "Kitabın konu anlatımında geçmiyor."
    ilk = re.split(r"(?<=[.!?])\s", t.aciklama, maxsplit=1)[0]
    return ilk


def madde(t: Tespit, no: int, bloklar: dict) -> dict:
    b: Blok | None = bloklar.get((t.sayfa_no, t.blok_no))
    konumlu = t.bbox != (0, 0, 0, 0) and list(t.bbox) != [0, 0, 0, 0]
    parca = t.metin_parcasi
    if t.alt_tur == "tema_yok" and (m := re.search(r"(\d+\. tema)", t.aciklama)):
        parca = f"{m.group(1)} ({t.metin_parcasi})"  # "SB.6.4" yerine "4. tema (SB.6.4)"
    alinti = None
    if b and konumlu:  # zor paragrafta paragrafın başı yeter; diğerlerinde kelimenin çevresi
        alinti = _alinti(b.metin, None, 70) if t.kriter == "okunabilirlik" else _alinti(b.metin, parca, 55)
    return {"no": no, "kriter": t.kriter, "tur": tur_adi(t.alt_tur), "oncelik": oncelik(t.guven_skoru),
            "sayfa": t.sayfa_no if konumlu else None, "basili": t.basili_sayfa_no if konumlu else None,
            "parca": parca, "kisa": kisa_aciklama(t), "aciklama": t.aciklama, "alinti": alinti}


def _say(maddeler: list[dict]) -> dict:
    c = Counter(m["oncelik"] for m in maddeler)
    return {"yüksek": c["yüksek"], "orta": c["orta"], "düşük": c["düşük"]}


def _turler(maddeler: list[dict]) -> list[list]:
    return [[ad, n] for ad, n in Counter(m["tur"] for m in maddeler if m["oncelik"] != "düşük").most_common()]


def _ornekler(maddeler: list[dict]) -> list[int]:
    sira = {"yüksek": 0, "orta": 1, "düşük": 2}
    adaylar = sorted((m for m in maddeler if m["oncelik"] != "düşük"), key=lambda m: (sira[m["oncelik"]], m["sayfa"] or 0))
    secilen, turler = [], set()
    for m in adaylar:  # önce farklı türlerden birer örnek
        if m["tur"] not in turler:
            secilen.append(m)
            turler.add(m["tur"])
    secilen += [m for m in adaylar if m not in secilen]
    return [m["no"] for m in sorted(secilen[:ORNEK_SAYISI], key=lambda m: m["sayfa"] or 0)]


def _liste(parcalar: list[str]) -> str:
    return parcalar[0] if len(parcalar) == 1 else ", ".join(parcalar[:-1]) + " ve " + parcalar[-1]


def yazim_cumleleri(maddeler: list[dict]) -> list[str]:
    s = _say(maddeler)
    goster = s["yüksek"] + s["orta"]
    if not maddeler:
        return ["Yazımda hata bulunmadı."]
    cumleler = []
    if goster:
        cumleler.append(f"Yazımda {goster} olası hata var." +
                        (f" {s['yüksek']} tanesine önce bakmanızı öneririz." if s["yüksek"] else ""))
        turler = _turler(maddeler)
        if len(turler) == 1:
            cumleler.append(f"Hepsi {turler[0][0]} türünde.")
        else:
            cumleler.append("Türlerine göre: " + _liste([f"{n} {ad}" for ad, n in turler[:4]])
                            + (" ve diğerleri." if len(turler) > 4 else "."))
    else:
        cumleler.append("Yazımda öne çıkan bir hata yok.")
    if s["düşük"]:
        cumleler.append(f"{s['düşük']} tespit daha düşük öncelikte: büyük ihtimalle terim, alıntı ya da PDF okuma "
                        f"sorunu. Listede duruyor, isterseniz bakarsınız.")
    return cumleler


def okunabilirlik_cumleleri(maddeler: list[dict], ozet: dict | None) -> list[str]:
    cumleler = []
    if ozet:
        cumleler.append(f"Kitabın dili genel olarak {ozet['atesman_duzeyi']} (Ateşman {str(ozet['atesman']).replace('.', ',')})"
                        + (f"; hedef sınıf {ozet['hedef_sinif']}." if ozet.get("hedef_sinif") else "."))
    if maddeler:
        cumleler.append(f"Kitabın geri kalanına göre belirgin biçimde zor {len(maddeler)} paragraf işaretlendi. "
                        f"Bunlar kesin hata değil, sadeleştirmeye aday yerler.")
    else:
        cumleler.append("Kitabın geri kalanından belirgin biçimde zor bir paragraf yok.")
    return cumleler


def mufredat_cumleleri(maddeler: list[dict]) -> list[str]:
    kavram = [m for m in maddeler if m["tur"] == tur_adi("kavram_yok")]
    tema = [m for m in maddeler if m["tur"] == tur_adi("tema_yok")]
    if not maddeler:
        return ["Öğretim programının anahtar kavramlarının hepsi kitabın konu anlatımında geçiyor."]
    cumleler = []
    if kavram:
        adlar = [m["parca"] for m in kavram if m["parca"]]
        cumleler.append(f"Programın {len(kavram)} anahtar kavramı kitabın konu anlatımında geçmiyor"
                        + (f": {_liste(adlar[:6])}." if adlar else "."))
    if tema:
        cumleler.append(f"Programın {len(tema)} teması ya da öğrenme alanı kitapta işlenmemiş görünüyor "
                        f"(başka bir ciltte olabilir).")
    return cumleler


def tutarlilik_cumleleri(maddeler: list[dict]) -> list[str]:
    if not maddeler:
        return ["Kitap içinde birbiriyle çelişen bilgi bulunmadı."]
    return [f"{len(maddeler)} yerde kitap kendi içinde çelişiyor olabilir. İki cümle yan yana gösteriliyor; "
            f"karar sizin."]


def kriter_ozeti(kriter: str, tespitler: list[Tespit] | None, bloklar: dict, ilk_no: int = 1,
                 okunabilirlik_ozeti: dict | None = None, neden: str | None = None) -> dict:
    """tespitler None ise kriter çalışmadı (neden yazılır)."""
    if tespitler is None:
        return {"ad": KRITERLER[kriter], "durum": "atlandı", "neden": neden or "Seçilmedi.", "cumleler": [],
                "sayilar": {}, "ornekler": [], "maddeler": []}
    maddeler = [madde(t, ilk_no + i, bloklar) for i, t in enumerate(
        sorted(tespitler, key=lambda t: (-t.guven_skoru, t.sayfa_no)))]
    cumleler = {"yazim": lambda: yazim_cumleleri(maddeler),
                "okunabilirlik": lambda: okunabilirlik_cumleleri(maddeler, okunabilirlik_ozeti),
                "mufredat": lambda: mufredat_cumleleri(maddeler),
                "tutarlilik": lambda: tutarlilik_cumleleri(maddeler)}[kriter]()
    return {"ad": KRITERLER[kriter], "durum": "tamam", "neden": neden, "cumleler": cumleler,
            "sayilar": _say(maddeler), "turler": _turler(maddeler), "ornekler": _ornekler(maddeler),
            "maddeler": maddeler}
