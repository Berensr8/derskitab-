"""Alıntı ayırma (F2, K28): kitaba başka bir yazardan alınmış metinleri (şiir, hikâye parçası, eski
metin, makale) bulur. Bu metinlerdeki kelime tespitleri kitabın yazım hatası değil, yazarın kendi
yazımı ya da eski Türkçe olabilir; silinmez, düşük önceliğe iner (K25 ile aynı yol).

Bir blok iki yoldan alıntı sayılır:
  1. İmza satırı: alıntıların altında yazarın adı olur ("Hüseyin Nihal Atsız", "Fuzûlî",
     "Anonim (haz.: …)"). İmza kısa, cümle gibi bitmeyen, bir adla başlayan satırdır; metinden küçük
     puntodadır ve metnin sağına girintili ya da sola hizalı hemen altındadır (aynı puntoysa alıntının
     sağ kenarına kadar uzanır). İmzanın üstünde, aynı sütunda ve aynı yazı tipindeki bloklar
     yukarı doğru alıntı sayılır ("(...)" atlama işaretleri araya girebilir; şiirde her dize ayrı
     blok olabilir — kelime sayısı alıntının tamamında hesaplanır).
  2. Eski dil: blokta Farsça tamlama ("kandîl-i sipihr") ya da "u/ü" bağlacı ("tâc u taht") var
     ve araçların tanımadığı en az 2 küçük harfli kelime geçiyor.
  3. Replik (v3, K29): tiyatro ve hikâye diyalogları. Sayfada büyük harfli konuşmacı adıyla başlayan
     ("KARAGÖZ — …", "HARPAGON: …") ya da konuşma çizgisiyle başlayan ("— Neler sorarlar?") en az
     3 blok varsa bunlar alıntıdır (konuşmacılı biçimde en az 2 farklı konuşmacı, biri tekrar konuşuyor,
     söz küçük harf içeriyor: içindekiler satırları — "OKUMA: ŞİİR" — ve tanım listeleri — "ADH: …" — elenir).
v3 (K29): imzalı alıntı sayfanın başına kadar çıkıyorsa önceki sayfaların sonundan aynı yazı tipiyle
devam eder (roman ve hikâye parçaları sayfalarca sürer; imza son sayfadadır). İmza metinle aynı puntoda olabilir, daha kalın yazılmış ve "Yazar, Eser" biçimindeyse
("Necip Fazıl Kısakürek, Çile" yarı kalın, şiir normal) — altında alıntının yazı tipinde devam eden
metin yoksa (başlık değil).
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
IMZA_SOL_PAY = 0  # (denendi: 250 punto TDE 9 s.36ya yarıyor ama harita etiketlerini imza yapıyordu)
IMZA_EN_KUCUK_PUNTO = 6  # harita etiketleri (2-4 punto) imza sayılmaz
IZAFET = re.compile(r"(?<![\w’'])[a-zçğıöşüâîû][^\W\d_]*-[ıiuü](?=[\s,.;:!?]|$)")
BAGLAC = re.compile(r"[^\W\d_]\s[uü]\s[^\W\d_]")
ATLAMA = re.compile(r"^\(?\s*(?:…|\.\.\.)\s*\)?$")
KUCUK_KELIME = re.compile(r"(?<![\w’'])[a-zçğıöşüâîû][^\W\d_]{2,}")
ALINTI_NOTU = "Alıntı metin"
KONUSMACI = re.compile(r"^\s*((?:[A-ZÇĞİÖŞÜÂÎÛl]{1,3}\.\s*)?[A-ZÇĞİÖŞÜÂÎÛ][A-ZÇĞİÖŞÜÂÎÛ’']+"
                       r"(?:\s[A-ZÇĞİÖŞÜÂÎÛ][A-ZÇĞİÖŞÜÂÎÛ’']+){0,2})\s*(?:—|:)\s+(.*)", re.S)
KONUSMA_CIZGISI = re.compile(r"^\s*—\s*\S")
REPLIK_EN_AZ = 3  # sayfada bu kadar replik bloğu olmalı
# Alıntı bölgesi yukarı çıkarken bu kadar puntodan büyük boş aralıkta durur (şiirde kıta arası ~22 punto;
# TDE 12 s.96'da şiirin sağ sütunu 80 punto yukarıdaki soruya ulaşıp onu da alıntı sayıyordu — K29 testi)
BOLGE_EN_FAZLA_BOSLUK = 36
ALINTI_EN_FAZLA_SAYFA = 6  # imzalı bir alıntı geriye doğru en fazla bu kadar sayfaya yayılır (Huzur parçası: 4)
_KALIN = re.compile(r"bold|semibold|demi|black|heavy|medium", re.I)


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


def _ustteki(b: Blok, sayfa_bloklari: list[Blok], sol_pay: float = 0) -> Blok | None:
    """Aynı sütunda (yatayda örtüşen) hemen üstteki blok. İmza satırı üstündeki metnin kutusuyla
    birkaç punto üst üste binebiliyor (TDE 10 s.38), bu yüzden 6 punto örtüşmeye izin verilir.
    sol_pay: sağa yaslı imzanın üstündeki son satır kısa olabilir ("— Ne var?", TDE 9 s.36); imza
    için soldaki bu kadar uzaklıktaki bloklar da sayılır."""
    adaylar = [x for x in sayfa_bloklari if x is not b and x.bbox[1] < b.bbox[1] - 1
               and x.bbox[3] <= b.bbox[1] + 6 and x.bbox[0] < b.bbox[2] and x.bbox[2] > b.bbox[0] - sol_pay]
    return max(adaylar, key=lambda x: x.bbox[3]) if adaylar else None


_PARANTEZ = re.compile(r"\([^)]*\)?")
_BAGLACLAR = {"ile", "ve", "de", "da", "u", "ü", "ve’"}


_SOYADI = re.compile(r"(?:oğlu|oğlan|zade)$")


@functools.cache
def _cozumler(kelime: str) -> list[str] | None:
    """Starlang çözümleri; Starlang bazı kelimelerde kendi içinde hata veriyor (TxtWord.removeFlag,
    TDE 11'de görüldü) — o zaman None (kelime ad sayılmaz: belirsizlikte tespit gizlenmez)."""
    try:
        c = yazim.starlang_cozumleyici().morphologicalAnalysis(kelime)
        return [c.getFsmParse(i).transitionList() for i in range(c.size())]
    except (ValueError, IndexError, KeyError):
        return None


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
    parcalar = _cozumler(kelime)
    if parcalar is None:
        return "degil"
    if not parcalar:
        return "olabilir"
    if any("+P3SG+NOM" in c or "+P3PL+NOM" in c for c in parcalar):
        return "tamlama"
    prop = ["+PROP" in c for c in parcalar]
    return "kesin" if all(prop) else "olabilir" if any(prop) else "degil"


_UNVANLAR = {"Âşık", "Aşık", "Şeyh", "Hacı"}
_SAPKALI = re.compile(r"[âîûÂÎÛ]")


def ad_gibi_mi(metin: str) -> bool:
    """Yazar adı gibi mi ("Hüseyin Nihal Atsız", "Bedri Rahmi Eyüboğlu, Karadut", "Anonim (haz.: …)").
    Virgülden önceki ad kısmı (unvanlar — Âşık, Şeyh, Hacı — atılır): rakam yok (v3: yalnız ad kısmında), en fazla 5 kelime, hepsi
    büyük harfle başlıyor, son kelime iyelik ekli değil; kelimelerin hepsi ad olabilir ya da en fazla
    biri sıradan ve en az biri kesin ad. Tek kelimelik imza: "Anonim", soyadı (Karacaoğlan) ya da
    sözlükte olmayan şapkalı mahlas (Fuzûlî, Bâkî, Necâtî).
    Elenenler: "Görsel 1.19", "Bilgi Kutusu", "Altay Dağları", "Ergenekon Destanı", "Trabzon"."""
    ad = _PARANTEZ.sub(" ", metin).split(",")[0]
    if any(c.isdigit() for c in ad):  # eser adında rakam olabilir ("Metin And, 100 Soruda Türk Tiyatrosu")
        return False
    kelimeler = [k.split("’")[0].split("-")[0] for k in ad.split() if k not in _BAGLACLAR]
    if not kelimeler or len(kelimeler) > 5 or not all(k[:1].isupper() for k in kelimeler):
        return False
    if kelimeler[0] == "Anonim":
        return True
    kelimeler = [k for k in kelimeler if k not in _UNVANLAR] or kelimeler
    if len(kelimeler) == 1:
        k = kelimeler[0]
        return bool(_SOYADI.search(k)) or (bool(_SAPKALI.search(k)) and _cozumler(k) == [])
    turler = [_ad_turu(k) for k in kelimeler]
    if turler[-1] == "tamlama":  # yer ve başlık adı ("Altay Dağları"); "Bedri Rahmi" gibi adlar ilk kelimelerde
        return False
    turler = ["olabilir" if t == "tamlama" else t for t in turler]
    return turler.count("degil") == 0 or (turler.count("degil") == 1 and "kesin" in turler)


def alinti_bolgesi(ust: Blok, sayfa_bloklari: list[Blok], bicimler: dict, alinti_bicimi=None) -> list[Blok]:
    """İmzanın üstünden yukarı: imzanın hemen üstündeki bloğun (ya da verilen) biçimdeki bloklar
    ("(...)" atlama işaretleri araya girebilir; şiirde her dize ayrı blok olabilir)."""
    alinti_bicimi = alinti_bicimi or bicimler.get((ust.sayfa_no, ust.blok_no))
    bolge = []
    while ust is not None:
        ust_bicim = bicimler.get((ust.sayfa_no, ust.blok_no))
        if ust_bicim == alinti_bicimi:
            bolge.append(ust)
        elif not ATLAMA.match(ust.metin.strip()):
            break
        onceki, ust = ust, _ustteki(ust, sayfa_bloklari)
        if ust is not None and onceki.bbox[1] - ust.bbox[3] > BOLGE_EN_FAZLA_BOSLUK:
            break
    return bolge


def imza_mi(b: Blok, ust: Blok | None, bolge: list[Blok], bicim, ust_bicim, alt_bicim=None) -> bool:
    """b, üstündeki alıntı bölgesinin imzası mı? alt_bicim: b'nin hemen altındaki bloğun biçimi
    (aynı puntodaki kalın ad satırı başlık mı imza mı ayırmak için)."""
    metin = b.metin.strip()
    if ust is None or not bolge or not bicim or not ust_bicim or not ad_gibi_mi(metin):
        return False
    if len(metin) > IMZA_EN_FAZLA_KARAKTER or metin[-1] in ".:?!;,*":
        return False
    if not IMZA_EN_KUCUK_PUNTO <= bicim[1] <= ust_bicim[1]:
        return False
    # Alıntı gerçek bir metin olmalı: toplam en az 8 kelime, kelimelerin en az %40'ı küçük harfle
    # başlıyor (harita etiketleri — "Bakü - Tiflis - Ceyhan Ham Petrol Boru Hattı" — elenir)
    kelimeler = [k for x in bolge for k in x.metin.split() if k[:1].isalpha()]
    if len(kelimeler) < 8 or sum(k[0].islower() for k in kelimeler) < 0.4 * len(kelimeler):
        return False
    sol, sag = min(x.bbox[0] for x in bolge), max(x.bbox[2] for x in bolge)
    girintili = b.bbox[0] - sol >= 30
    sola_hizali_altta = abs(b.bbox[0] - ust.bbox[0]) <= 5 and b.bbox[1] - ust.bbox[3] <= IMZA_EN_FAZLA_BOSLUK
    if bicim[1] == ust_bicim[1]:  # metinle aynı punto: girintili ve alıntının sağ kenarına kadar uzanıyor
        if girintili and b.bbox[2] >= sag - 6:
            return True
        # ya da metinden kalın ve "Yazar, Eser" biçiminde (v3). Kalın tek ad başlık olabilir ("Mavi Vatan",
        # "Divanü Lügati't-Türk" — Sosyal 6'da kitabın kendi metninin altında); altında alıntının yazı
        # tipiyle devam eden metin varsa da başlıktır
        kalin = bool(_KALIN.search(bicim[0])) and not _KALIN.search(ust_bicim[0])
        return kalin and "," in metin and alt_bicim != ust_bicim and (girintili or sola_hizali_altta)
    # Küçük punto: metnin sağına girintili (çoğu imza) ya da sola hizalı ve hemen altında (iki sütunlu şiirler)
    return girintili or sola_hizali_altta


def eski_dil_mi(b: Blok, denetciler) -> bool:
    """Farsça tamlama ("kandîl-i") ya da "u/ü" bağlacı var ve araçların tanımadığı en az 2 küçük
    harfli kelime geçiyor."""
    if not (IZAFET.search(b.metin) or BAGLAC.search(b.metin)):
        return False
    taninmayan = [k for k in KUCUK_KELIME.findall(b.metin)
                  if not (yazim._gecerli(denetciler[0], k) and yazim._gecerli(denetciler[1], k))]
    return len(taninmayan) >= 2


def _alttaki(b: Blok, sayfa_bloklari: list[Blok]) -> Blok | None:
    """Aynı sütunda hemen alttaki blok (en fazla IMZA_EN_FAZLA_BOSLUK uzaklıkta)."""
    adaylar = [x for x in sayfa_bloklari if x is not b and b.bbox[3] - 6 <= x.bbox[1] <= b.bbox[3] + IMZA_EN_FAZLA_BOSLUK
               and x.bbox[0] < b.bbox[2] and x.bbox[2] > b.bbox[0]]
    return min(adaylar, key=lambda x: x.bbox[1]) if adaylar else None


def replik_bloklari(sayfa_bloklari: list[Blok]) -> dict:
    """{(sayfa_no, blok_no): sebep} — sayfadaki tiyatro/hikâye replikleri (en az REPLIK_EN_AZ blok)."""
    konusmali, konusmacilar = [], Counter()
    for b in sayfa_bloklari:
        m = KONUSMACI.match(b.metin)
        if m and any(c.islower() for c in m.group(2)):
            konusmali.append(b)
            konusmacilar[m.group(1).split(".")[-1].strip()] += 1
    sonuc = {}
    # Diyalogda en az iki konuşmacı olur ve biri tekrar konuşur (her biri bir kez geçen etiketler —
    # "ACTH: …, ADH: …, FSH: …" — kitabın kendi tanım listesidir, Biyoloji 11)
    if len(konusmali) >= REPLIK_EN_AZ and len(konusmacilar) >= 2 and max(konusmacilar.values()) >= 2:
        sonuc |= {(b.sayfa_no, b.blok_no): "tiyatro repliği" for b in konusmali}
    cizgili = [b for b in sayfa_bloklari if KONUSMA_CIZGISI.match(b.metin)]
    if len(cizgili) >= REPLIK_EN_AZ:
        sonuc |= {(b.sayfa_no, b.blok_no): "diyalog" for b in cizgili if (b.sayfa_no, b.blok_no) not in sonuc}
    return sonuc


def onceki_sayfalara_uzat(bolge: list[Blok], sayfalar: dict, bicimler: dict) -> list[Blok]:
    """Bölge sayfanın başına kadar çıkıyorsa önceki sayfanın sonundaki (aynı sütun, aynı yazı tipi)
    bloktan yukarı devam eder; yazı tipi değişen bir blokta (başlık, yönerge) durur."""
    ek, ust = [], bolge[-1]
    alinti_bicimi = bicimler.get((bolge[0].sayfa_no, bolge[0].blok_no))
    sol, sag = min(x.bbox[0] for x in bolge), max(x.bbox[2] for x in bolge)
    for _ in range(ALINTI_EN_FAZLA_SAYFA - 1):
        if _ustteki(ust, sayfalar.get(ust.sayfa_no, [])) is not None:
            break  # bölge bu sayfada bir başlıkta durdu
        onceki = [x for x in sayfalar.get(ust.sayfa_no - 1, [])
                  if x.bbox[0] < sag and x.bbox[2] > sol and not x.metin.strip().isdigit()]  # sayfa numarası değil
        if not onceki:
            break
        alt = max(onceki, key=lambda x: x.bbox[3])
        if bicimler.get((alt.sayfa_no, alt.blok_no)) != alinti_bicimi:
            break
        parca = alinti_bolgesi(alt, onceki, bicimler, alinti_bicimi)
        ek += parca
        ust = parca[-1]
    return ek


def alinti_bloklari(bloklar: list[Blok], bicimler: dict, denetciler=None) -> dict:
    """{(sayfa_no, blok_no): sebep} — sebep imzanın metni ya da "eski dil"."""
    denetciler = denetciler or yazim.varsayilan_denetciler()
    sayfalar = {}
    for b in bloklar:
        sayfalar.setdefault(b.sayfa_no, []).append(b)
    sonuc = {}
    for sayfa_bloklari in sayfalar.values():
        for b in sayfa_bloklari:
            ust = _ustteki(b, sayfa_bloklari, sol_pay=IMZA_SOL_PAY)
            if ust is None:
                continue
            bolge = alinti_bolgesi(ust, sayfa_bloklari, bicimler)
            alt = _alttaki(b, sayfa_bloklari)
            if imza_mi(b, ust, bolge, bicimler.get((b.sayfa_no, b.blok_no)), bicimler.get((ust.sayfa_no, ust.blok_no)),
                       bicimler.get((alt.sayfa_no, alt.blok_no)) if alt else None):
                for x in bolge + onceki_sayfalara_uzat(bolge, sayfalar, bicimler):
                    sonuc[(x.sayfa_no, x.blok_no)] = b.metin.strip()
        for anahtar, sebep in replik_bloklari(sayfa_bloklari).items():
            sonuc.setdefault(anahtar, sebep)
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
        kaynak = {"eski dil": "eski Türkçe ya da edebî dil işaretleri var", "tiyatro repliği": "tiyatro repliği",
                  "diyalog": "hikâye diyaloğu"}.get(sebep, f"kaynak: {sebep}")
        sonuc.append(replace(t, guven_skoru=min(t.guven_skoru, DUSUK_GUVEN), aciklama=t.aciklama +
                             f" {ALINTI_NOTU} ({kaynak}): kelime yazarın kendi yazımı ya da eski yazım olabilir"
                             " — düşük öncelik."))
    return sonuc


def pdf_ile_isaretle(pdf_yolu, bloklar: list[Blok], tespitler: list[Tespit]) -> list[Tespit]:
    """Kelime tespiti olan sayfalarda alıntıları bulur ve işaretler (yazı tipleri PDF'ten okunur).
    İmzası sonraki sayfalarda olabileceği için tespitli sayfaların ardındaki sayfalar da okunur."""
    tespitli = {t.sayfa_no for t in tespitler if t.alt_tur == "morfoloji"}
    if not tespitli:
        return tespitler
    sayfalar = {s + i for s in tespitli for i in range(ALINTI_EN_FAZLA_SAYFA)}
    ilgili = [b for b in bloklar if b.sayfa_no in sayfalar]
    return alintilari_isaretle(tespitler, alinti_bloklari(ilgili, blok_bicimleri(pdf_yolu, ilgili)))
