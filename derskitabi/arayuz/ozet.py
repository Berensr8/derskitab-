"""Sonuç ekranının içeriği: her kriter için basit cümleler, örnek alıntılar ve tek tek inceleme listesi.

Cümleler burada kurulur (ekran yalnız gösterir), böylece test edilebilir. Öncelik Excel/PDF'tekiyle aynı
kurala dayanır (güven ≥ 0,75 / ≥ 0,5 / < 0,5) ama ekranda tek bir sözlükle anlatılır: "öncelikli",
"kontrol edilecek", "düşük öncelikli". Öncelik yalnız olası HATALARA (yazım, çelişki) verilir; zor
paragraflar ve müfredat notları hata değildir, sayılırlar ama "öncelikli" sayılmazlar (2026-11-05
arayüz incelemesi: "72 yere önce bakın" üç farklı şeyi topluyordu).
"""

import re
from collections import Counter

from ..kriterler.dusuk_oncelik import NOTLAR
from ..model import Blok, Tespit
from ..pdf_notlari import oncelik
from ..rapor import TUR_ADLARI

KRITERLER = {"yazim": "Yazım ve dil", "okunabilirlik": "Dilsel karmaşıklık",
             "mufredat": "Müfredat (öğretim programı)", "tutarlilik": "Bilgi tutarsızlığı"}
ONCELIKLI = ("yazim", "tutarlilik")  # yalnız bunlar olası hata; öncelik verilir
ONCELIK_ADI = {"yüksek": "öncelikli", "orta": "kontrol edilecek", "düşük": "düşük öncelikli"}
ORNEK_SAYISI = 3
_SADE_TUR = {"morfoloji": "kelime yazımı", "kitap_ici_zor_paragraf": "zor paragraf",
             "noktalama_bosluk": "noktalamadan sonra boşluk eksik", "ozel_ad_kesme": "özel ada gelen ekte kesme eksik",
             "kisaltma_kesme": "kısaltmaya gelen ekte kesme eksik", "sayi_kesme": "sayıya gelen ekte kesme eksik"}
# Sistemin ölçülmüş başarısı, kullanıcının diliyle (kaynak: testseti/*_sonuclari.md; rapor.py OLCULEN_BASARI)
GUVEN = {
    "yazim": "Ne kadar güvenilir? Bilerek eklenen 56 yazım hatasının 55'ini buldu. Ama gerçek kitaplarda "
             "işaretlenen kelimelerin bir kısmı terim, özel ad ya da alıntı çıkıyor; her birine göz atın.",
    "okunabilirlik": "Ne kadar güvenilir? Ölçüler cümle ve kelime uzunluğuna dayanır; sınıf düzeyini kesin "
                     "ayırt etmez. İşaretler 'buraya bir bakın' anlamındadır.",
    "mufredat": "Ne kadar güvenilir? Yalnız kitapta hiç geçmeyen kavramları yakalar; bir konunun yeterince "
                "işlenip işlenmediğini değerlendirmez.",
    "tutarlilik": "Ne kadar güvenilir? Bilerek eklenen 35 çelişkinin 27'sini buldu ve bulduklarının hepsi "
                  "gerçekten çelişkiydi; ama her çelişkiyi yakalamaz.",
}
HAKEMSIZ = ("Bu incelemede yapay zekâ hakemi kapalıydı; açık olsaydı terim ve özel adlardan gelen yanlış "
            "alarmların çoğu düşük önceliğe inerdi.")


def tur_adi(alt_tur: str | None) -> str:
    ad = _SADE_TUR.get(alt_tur) or TUR_ADLARI.get(alt_tur or "", alt_tur or "diğer")
    return ad.removeprefix("TDK kuralı: ")


def _sayi(metin: str) -> str:
    return metin.replace(".", ",")


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
    while 0 < bas < i and metin[bas - 1] != " ":  # kelime ortasından kesme
        bas += 1
    while i + len(parca) < son < len(metin) and metin[son] != " ":
        son -= 1
    return {"once": ("…" if bas > 0 else "") + metin[bas:i], "vurgu": parca,
            "sonra": metin[i + len(parca):max(son, i + len(parca))] + ("…" if son < len(metin) else "")}


def _noktalama_parcasi(parca: str) -> str:
    """"ikiye katlandı.Takım arkada" → "katlandı.Takım": yalnız boşluksuz birleşen iki kelime vurgulanır."""
    m = re.search(r"\S*[.,;:!?]\S+", parca)
    return m.group(0) if m else parca


def _okunabilirlik_olculeri(aciklama: str) -> dict:
    m = re.search(r"Cümle başına ortalama ([\d.]+) kelime \(kitap ortancası ([\d.]+)\), kelime başına ([\d.]+) hece",
                  aciklama)
    return {"kelime": float(m.group(1)), "ortanca": float(m.group(2)), "hece": float(m.group(3))} if m else {}


def kisa_aciklama(t: Tespit) -> str:
    """Listede görünen tek cümle; ayrıntıda sade_aciklama, en altta teknik açıklama."""
    if t.kriter == "yazim" and t.alt_tur == "morfoloji":
        oneri = re.search(r"Önerilen yazım: '([^']+)'", t.aciklama)
        return "Sözlükte bulunamadı, yanlış yazılmış olabilir" + (f" (önerilen: {oneri.group(1)})" if oneri else "") + "."
    if t.kriter == "tutarlilik":  # 's. 241: "A" ile s. 256: "B" çelişiyor olabilir …' → karşı cümle
        m = re.match(r's\. (\S+): "(.+?)" ile s\. (\S+): "(.+?)" çelişiyor', t.aciklama)
        if m:
            kendi_ilk = bool(t.metin_parcasi) and t.metin_parcasi[:30] in m.group(2)
            konum, karsi = (m.group(3), m.group(4)) if kendi_ilk else (m.group(1), m.group(2))
            return f"Şu bilgiyle çelişiyor olabilir (s. {konum}): “{karsi}”"
        return "Kitabın başka bir yerindeki bilgiyle çelişiyor olabilir."
    if t.kriter == "okunabilirlik":
        o = _okunabilirlik_olculeri(t.aciklama)
        if o and o["kelime"] >= 1.3 * o["ortanca"]:
            return (f"Cümleler uzun: ortalama {round(o['kelime'])} kelime (kitapta genelde {round(o['ortanca'])}).")
        if o:
            hece = _sayi(f"{o['hece']:.1f}")
            return f"Kelimeler uzun ve ağır: kelime başına ortalama {hece} hece."
        return "Kitabın geri kalanına göre belirgin biçimde zor."
    if t.kriter == "mufredat":
        if t.alt_tur == "tema_yok":
            return "Bu temanın anahtar kavramlarının çoğu kitapta geçmiyor; tema başka bir ciltte olabilir."
        if "tanıtım" in t.aciklama:
            return "Yalnız tanıtım ya da kapak sayfasında geçiyor, konu anlatımında yok."
        return "Kitabın konu anlatımında geçmiyor."
    return re.split(r"(?<=[.!?])\s", t.aciklama, maxsplit=1)[0]


def sade_aciklama(t: Tespit) -> str:
    """Ayrıntıda gösterilen açıklama: araç ve model adları, formül puanları olmadan."""
    a = t.aciklama
    if t.kriter == "yazim" and t.alt_tur == "morfoloji":
        cumleler = ["Sözlükte bulunamadı; yanlış yazılmış olabilir."]
        cumleler.append("İki ayrı denetim aracı da tanımadı." if "iki araç da" in a
                        else "Denetim araçlarından biri tanımadı, öbürü tanıdı.")
        if m := re.search(r"Sondaki '([^']+)' ayrılınca geçerli bir kelime kalıyor: ([^.]+)", a):
            cumleler.append(f"Sondaki '{m.group(1)}' ayrılınca anlamlı bir kelime kalıyor: {m.group(2)}.")
        if "de yazım hatası dedi" in a:
            cumleler.append("Yapay zekâ hakemi de hata dedi.")
        if m := re.search(r"Önerilen yazım: '([^']+)'", a):
            cumleler.append(f"Önerilen yazım: {m.group(1)}.")
        if "muhtemelen doğru" in a:
            cumleler.append("Yapay zekâ hakemi muhtemelen doğru yazıldığını düşünüyor (terim, özel ad ya da alıntı).")
        if m := re.search(r"kitapta geçen '([^']+)' kelimesine", a):
            cumleler.append(f"Kitapta geçen '{m.group(1)}' kelimesine çok benziyor; yazım hatası olabilir.")
        for not_, ad in NOTLAR.items():
            if not_ in a:  # düşük öncelik sebebi önce söylenir
                cumleler = [{"PDF okuma parçası": "Büyük ihtimalle hata değil: kitabın değil, PDF'in okunmasının sorunu.",
                             "terim": "Büyük ihtimalle hata değil: kitabın kendi açıkladığı bir terim.",
                             "alıntı içinde": "Büyük ihtimalle hata değil: bir alıntının içinde (yazarın ya da "
                                              "eski yazım)."}[ad], "Sözlükte bulunmadığı için işaretlendi."]
                break
        return " ".join(cumleler)
    if t.kriter == "okunabilirlik":
        o = _okunabilirlik_olculeri(a)
        duzey = re.search(r"\((\d+–\d+\. sınıf)\)", a)
        parcalar = ["Bu paragraf kitabın en zor bölümleri arasında."]
        if o:
            hece = _sayi(f"{o['hece']:.1f}")
            parcalar.append(f"Cümle başına ortalama {round(o['kelime'])} kelime (kitapta genelde {round(o['ortanca'])}), "
                            f"kelime başına {hece} hece.")
        if duzey:
            parcalar.append(f"Formüllere göre {duzey.group(1)} düzeyinde okunuyor.")
        return " ".join(parcalar)
    if t.kriter == "tutarlilik":
        a = re.sub(r"\(iki model de \([^)]*\)\)", "(iki ayrı yapay zekâ modeli de çelişki gördü)", a)
        return re.sub(r"\(yalnız [^)]*\)", "(yapay zekâ modellerinden biri çelişki gördü)", a)
    return a


def madde(t: Tespit, no: int, bloklar: dict) -> dict:
    b: Blok | None = bloklar.get((t.sayfa_no, t.blok_no))
    konumlu = t.bbox != (0, 0, 0, 0) and list(t.bbox) != [0, 0, 0, 0]
    parca = t.metin_parcasi
    if t.alt_tur == "tema_yok" and (m := re.search(r"(\d+\. tema)", t.aciklama)):
        parca = f"{m.group(1)} ({t.metin_parcasi})"  # "SB.6.4" yerine "4. tema (SB.6.4)"
    if t.alt_tur == "noktalama_bosluk" and parca:
        parca = _noktalama_parcasi(parca)
    alinti = None
    if b and konumlu:  # zor paragrafta paragrafın başı yeter; diğerlerinde kelimenin çevresi
        alinti = _alinti(b.metin, None, 70) if t.kriter == "okunabilirlik" else _alinti(b.metin, parca, 55)
    return {"no": no, "kriter": t.kriter, "tur": tur_adi(t.alt_tur),
            "oncelik": oncelik(t.guven_skoru) if t.kriter in ONCELIKLI else None,
            "sayfa": t.sayfa_no if konumlu else None, "basili": t.basili_sayfa_no if konumlu else None,
            "blok": t.blok_no if konumlu else None, "parca": parca, "kisa": kisa_aciklama(t),
            "sade": sade_aciklama(t), "aciklama": t.aciklama, "alinti": alinti}


def _say(maddeler: list[dict]) -> dict:
    c = Counter(m["oncelik"] for m in maddeler)
    return {"yüksek": c["yüksek"], "orta": c["orta"], "düşük": c["düşük"]}


def _turler(maddeler: list[dict]) -> list[list]:
    return [[ad, n] for ad, n in Counter(m["tur"] for m in maddeler if m["oncelik"] != "düşük").most_common()]


def _ornekler(maddeler: list[dict]) -> list[int]:
    sira = {"yüksek": 0, "orta": 1, None: 1, "düşük": 2}
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
        cumleler.append(f"Yazımda {goster} olası hata var." + (
            f" Önce bakılması gerekenler: {s['yüksek']}." if s["yüksek"] and s["orta"] else ""))
        turler = _turler(maddeler)
        if len(turler) == 1:
            cumleler.append(f"Hepsi {turler[0][0]} türünde.")
        else:
            cumleler.append("Türlerine göre: " + ", ".join(f"{ad} ({n})" for ad, n in turler[:4])
                            + (" ve diğerleri." if len(turler) > 4 else "."))
    else:
        cumleler.append("Yazımda öne çıkan bir hata yok.")
    if s["düşük"]:
        cumleler.append(f"{s['düşük']} yer daha var ama büyük ihtimalle hata değil (terim, alıntı ya da PDF okuma "
                        f"sorunu); listede 'düşük öncelikli' olarak duruyor.")
    return cumleler


def okunabilirlik_cumleleri(maddeler: list[dict], ozet: dict | None) -> list[str]:
    cumleler = []
    if ozet:
        cumleler.append(f"Kitabın dili genel olarak {ozet['atesman_duzeyi']} (Ateşman puanı "
                        f"{round(ozet['atesman'])}; puan yükseldikçe metin kolaylaşır).")
    if maddeler:
        cumleler.append(f"{len(maddeler)} paragraf kitabın geri kalanından belirgin biçimde zor. Bunlar hata değil, "
                        f"sadeleştirmeye aday yerler.")
    else:
        cumleler.append("Kitabın geri kalanından belirgin biçimde zor bir paragraf yok.")
    return cumleler


def mufredat_cumleleri(maddeler: list[dict]) -> list[str]:
    kavram = [m for m in maddeler if m["tur"] == tur_adi("kavram_yok")]
    tema = [m for m in maddeler if m["tur"] == tur_adi("tema_yok")]
    if not maddeler:
        return ["Programın anahtar kavramlarının hepsi kitabın konu anlatımında geçiyor."]
    cumleler = []
    if kavram:
        adlar = [m["parca"] for m in kavram if m["parca"]]
        cumleler.append(f"Programın {len(kavram)} anahtar kavramı kitabın konu anlatımında geçmiyor"
                        + (f": {_liste(adlar[:6])}." if adlar else "."))
    if tema:
        cumleler.append(f"Programın {len(tema)} teması kitapta işlenmemiş görünüyor (başka bir ciltte olabilir).")
    return cumleler


def tutarlilik_cumleleri(maddeler: list[dict], karsilastirma: int | None = None, hazir: bool = False) -> list[str]:
    kac = (f"Birbirine benzeyen {karsilastirma:,} cümle çifti karşılaştırıldı".replace(",", ".")
           if karsilastirma else "")
    ek = " (bu kitap için daha önce yapılmış karşılaştırma kullanıldı)" if hazir else ""
    if not maddeler:
        return [(f"{kac}{ek}; " if kac else "") + ("çelişki bulunmadı." if kac else "Kitap içinde birbiriyle çelişen bilgi bulunmadı.")]
    return [f"{len(maddeler)} yerde kitap kendi içinde çelişiyor olabilir. Her birinde çelişen iki cümleyi "
            f"alıntıladık; karar sizin."] + ([f"{kac}{ek}."] if kac else [])


def kriter_ozeti(kriter: str, tespitler: list[Tespit] | None, bloklar: dict, ilk_no: int = 1,
                 okunabilirlik_ozeti: dict | None = None, neden: str | None = None,
                 hakem: bool | None = None, karsilastirma: int | None = None, hazir: bool = False) -> dict:
    """tespitler None ise kriter çalışmadı (neden yazılır). hakem: yazımda yapay zekâ hakemi çalıştı mı;
    karsilastirma: tutarlılıkta karşılaştırılan aday çift sayısı (hazir: önceden hesaplanmış sonuç)."""
    if tespitler is None:
        return {"ad": KRITERLER[kriter], "durum": "atlandı", "neden": neden or "Seçilmedi.", "cumleler": [],
                "sayilar": {}, "ornekler": [], "maddeler": [], "guven": None}
    maddeler = [madde(t, ilk_no + i, bloklar) for i, t in enumerate(
        sorted(tespitler, key=lambda t: (-t.guven_skoru, t.sayfa_no)))]
    cumleler = {"yazim": lambda: yazim_cumleleri(maddeler),
                "okunabilirlik": lambda: okunabilirlik_cumleleri(maddeler, okunabilirlik_ozeti),
                "mufredat": lambda: mufredat_cumleleri(maddeler),
                "tutarlilik": lambda: tutarlilik_cumleleri(maddeler, karsilastirma, hazir)}[kriter]()
    guven = GUVEN[kriter] + (" " + HAKEMSIZ if kriter == "yazim" and hakem is False and maddeler else "")
    return {"ad": KRITERLER[kriter], "durum": "tamam", "neden": neden, "cumleler": cumleler,
            "sayilar": _say(maddeler) if kriter in ONCELIKLI else {}, "turler": _turler(maddeler),
            "ornekler": _ornekler(maddeler), "maddeler": maddeler, "guven": guven, "oncelikli": kriter in ONCELIKLI}
