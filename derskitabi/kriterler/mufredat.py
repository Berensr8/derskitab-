"""Müfredat uyumu (Faz 3, K31): kitabın MEB öğretim programındaki öğrenme çıktılarını karşılayıp karşılamadığı.

Girdi : kitabın blokları + Türkiye Yüzyılı Maarif Modeli öğretim programı (PDF, tymm.meb.gov.tr)
Çıktı : her öğrenme çıktısı için kapsam kararı ve kitaptaki sayfalar; karşılanmayan çıktılar ve kitapta
        geçmeyen anahtar kavramlar tespit olarak (kriter="mufredat")

İki parça:
  1. Anahtar kavram kontrolü (kural tabanlı): programın her çıktı grubu için verdiği anahtar kavramlar
     kitapta geçiyor mu, hangi sayfalarda.
  2. Çıktı kapsamı: çıktının adı ve içerik çerçevesi bge-m3 ile kitabın paragraflarına benzetilir; en
     yakın paragraflar sayfalarıyla gemma4'e sorulur: karşılanıyor / kısmen / karşılanmıyor. Beceri
     değil konu kapsamı sorulur (çıktılar "bilgi toplayabilme" gibi beceri diliyle yazılıyor).

Ürüne giren (K31 eki): yalnız anahtar kavram kontrolü. Çıktı kapsamı (dil modeli) önceden yazılan ölçütü
temiz doğrulamada geçmedi (Biyoloji 11 pozitif 0,82 < 0,85; eksik tema testi 5/10); --kapsam ile deneysel.

Kullanım:
    python -m derskitabi.kriterler.mufredat veri/biyoloji9.pdf            (program ve sınıf otomatik)
    python -m derskitabi.kriterler.mufredat veri/kitap.pdf --temalar 1-3 --kapsam
"""

import argparse
import json
import re
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pymupdf

from .. import yerel_model
from ..donanim import Bekci
from ..kayit import bloklari_yukle, json_kaydet, tespitleri_kaydet
from ..model import Blok, Tespit
from ..satirlar import birlesik_bloklar
from . import yazim

HAKEM_MODELI = "gemma4:12b-it-qat"
EN_YAKIN = 5  # hakeme gösterilen paragraf sayısı
EN_AZ_KELIME = 12  # bu kadar kelimeden kısa bloklar paragraf sayılmaz (başlık, etiket)
KARARLAR = ("karsilaniyor", "kismen", "karsilanmiyor")
_CIKTI = re.compile(r"(?m)^\s*(?:ÖĞRENME ÇIKTILARI\s*\n\s*VE SÜREÇ BİLEŞENLERİ\s*)?"
                    r"((?:BİY|SB)\.(\d+)\.(\d+)\.(\d+))\.\s+(.+?)\n\s*a\)", re.S)
_ICERIK = re.compile(r"İÇERİK ÇERÇEVESİ(.*?)Anahtar Kavramlar(.*?)ÖĞRENME\s*\n?\s*KANITLARI", re.S)
# Kitapta tanıtım sayfası işaretleri: "İÇERİK ÇERÇEVESİ" (tema kapağı), "BU ÖĞRENME ALANINDA" (Sosyal Bilgiler
# alan kapağı), "TEMA TEMA" (kapaktaki büyük yazı), "Tema sunusu", "Kitabın tanıtımı", "İçindekiler"
_TANITIM = re.compile(r"İÇERİK ÇERÇEVESİ|BU ÖĞRENME ALANINDA|\bTEMA\s+TEMA\b|(?i:öğrenilecek anahtar kavramlar|"
                      r"tema sunusu|kitabın tanıtımı|kitabımızı tanıyalım|^\s*içindekiler\s*$)", re.M)


@dataclass
class Cikti:
    kod: str
    sinif: int
    tema: int
    ad: str
    icerik: str = ""
    kavramlar: list[str] = field(default_factory=list)


_ALTLIK = re.compile(r"\s*\d+\s+[^,\n]*?DERSİ ÖĞRETİM PROGRAMI")  # programın sayfa altlığı ("50 BİYOLOJİ DERSİ …")


def _sade(metin: str) -> str:
    return " ".join(_ALTLIK.sub(" ", metin.replace("-\n", "")).split())


def program_ciktilari(pdf_yolu) -> list[Cikti]:
    """Programdaki öğrenme çıktıları; her biri ait olduğu grubun içerik çerçevesi ve anahtar kavramlarıyla."""
    with pymupdf.open(pdf_yolu) as belge:
        metin = "\n".join(s.get_text() for s in belge)
    ciktilar, grup = {}, []
    olaylar = sorted([(m.start(), "cikti", m) for m in _CIKTI.finditer(metin)] +
                     [(m.start(), "icerik", m) for m in _ICERIK.finditer(metin)], key=lambda x: x[0])
    for _, tur, m in olaylar:
        if tur == "cikti":
            kod = m.group(1)
            if kod not in ciktilar:  # ilk geçiş tanımdır; sonrakiler uygulama bölümündeki atıflar
                ciktilar[kod] = Cikti(kod, int(m.group(2)), int(m.group(3)), _sade(m.group(5)))
                grup.append(ciktilar[kod])
        else:
            icerik = _sade(m.group(1))
            kavramlar = [k.strip() for k in _sade(m.group(2)).split(",") if k.strip()]
            for c in grup:
                c.icerik, c.kavramlar = icerik, kavramlar
            grup = []
    return list(ciktilar.values())


def _kavram_deseni(kavram: str) -> re.Pattern:
    """Kavram, sonuna ek alabilecek şekilde aranır ("ökaryot" → "ökaryotlar"); çok kelimelide son kelime ek alır."""
    kelimeler = [re.escape(yazim.tr_kucuk(k)) for k in kavram.split()]
    return re.compile(r"(?<![^\W\d_])" + r"\s+".join(kelimeler) + r"[^\W\d_]{0,8}(?![^\W\d_])")


def tanitim_sayfalari(bloklar: list[Blok]) -> set[int]:
    """İçindekiler, kitabı tanıtım, tema / öğrenme alanı kapakları ve tema sunusu sayfaları. Bu sayfalar
    programın içerik çerçevesini ve anahtar kavramlarını aynen aktarıyor: konunun işlendiğini göstermezler."""
    return {b.sayfa_no for b in bloklar if _TANITIM.search(b.metin)}


def _kelime_desenleri(kavram: str) -> list[re.Pattern]:
    """Çok kelimeli kavramın kelimeleri ayrı ayrı, ek ve iyelik payıyla ("ısı dengesi" → "ısı", "deng…")."""
    kokler = [k if len(k) <= 4 else k[:max(4, len(k) - 3)] for k in yazim.tr_kucuk(kavram).split()]
    return [re.compile(r"(?<![^\W\d_])" + re.escape(k)) for k in kokler]


def _sayfa_metinleri(bloklar: list[Blok], tanitim: set[int], tanitim_mi: bool) -> dict[int, str]:
    sayfa_metni = {}
    for b in bloklar:
        if (b.sayfa_no in tanitim) == tanitim_mi:
            sayfa_metni[b.sayfa_no] = sayfa_metni.get(b.sayfa_no, "") + " " + yazim.tr_kucuk(b.metin)
    return sayfa_metni


def kavram_sayfalari(kavramlar: list[str], bloklar: list[Blok]) -> dict[str, list[int]]:
    """{kavram: kitapta geçtiği sayfalar} (tanıtım sayfaları sayılmaz). Kavram aynen geçmiyorsa çok kelimeli
    kavramın bütün kelimelerinin aynı sayfada geçtiği sayfalar ("kan basıncı dengesi" ↔ "kan basıncını düzenleyen")."""
    sayfa_metni = _sayfa_metinleri(bloklar, tanitim_sayfalari(bloklar), False)
    sonuc = {}
    for k in kavramlar:
        bulunan = set()
        for v in _bicimler(k):
            bulunan |= {s for s, m in sayfa_metni.items() if _kavram_deseni(v).search(m)}
            if not bulunan and len(v.split()) > 1:
                desenler = _kelime_desenleri(v)
                bulunan |= {s for s, m in sayfa_metni.items() if all(d.search(m) for d in desenler)}
        sonuc[k] = sorted(bulunan)
    return sonuc


def _bicimler(kavram: str) -> list[str]:
    """Kavramın aranacak biçimleri: parantezsiz hâli ve parantez içi ("sivil toplum kuruluşu (STK)"); tireli
    sıralama kelimelere ayrılır ("üretim-dağıtım-tüketim" → "üretim dağıtım tüketim")."""
    ana = re.sub(r"\s*\([^)]*\)", "", kavram).strip()
    parantez = re.findall(r"\(([^)]*)\)", kavram)
    return [re.sub(r"(?<=\w)[-–](?=\w)", " ", b) for b in [ana, *parantez] if b]


def yalniz_tanitimda(kavram: str, bloklar: list[Blok]) -> list[int]:
    """Kavramın geçtiği tanıtım sayfaları (kapak, içindekiler): kavram kitapta yalnız orada anılıyor olabilir."""
    sayfa_metni = _sayfa_metinleri(bloklar, tanitim_sayfalari(bloklar), True)
    return [s for s, m in sorted(sayfa_metni.items()) if _kavram_deseni(kavram).search(m)]


def paragraflar(bloklar: list[Blok]) -> list[Blok]:
    tanitim = tanitim_sayfalari(bloklar)
    return [b for b in birlesik_bloklar(bloklar)
            if b.tur == "paragraf" and len(b.metin.split()) >= EN_AZ_KELIME and b.sayfa_no not in tanitim]


SISTEM = """Sen MEB öğretim programlarını bilen bir ders kitabı inceleme uzmanısın. Sana bir öğrenme çıktısı ve bir ders kitabından bu çıktıya en çok benzeyen paragraflar (sayfa numaralarıyla) verilecek. Görevin: kitabın bu çıktının KONUSUNU işleyip işlemediğine karar vermek. Çıktının beceri ifadesine (bilgi toplama, sorgulama vb.) değil, konusuna bak.
- "karsilaniyor": paragraflar çıktının konusunu açıkça ve doğrudan işliyor.
- "kismen": konuya değiniliyor ama eksik ya da yalnız dolaylı.
- "karsilanmiyor": paragraflar başka konulardan bahsediyor; çıktının konusu bu paragraflarda yok.
Önce kısa bir Türkçe gerekçe yaz (en fazla iki cümle), sonra kararını ver."""


def ollama_kapsam_hakemi(cikti: Cikti, adaylar: list[Blok]) -> dict:
    metinler = "\n\n".join(f"[s. {b.basili_sayfa_no or b.sayfa_no}] {b.metin[:700]}" for b in adaylar)
    soru = (f"Öğrenme çıktısı ({cikti.kod}): {cikti.ad}\nİçerik çerçevesi: {cikti.icerik[:600]}\n\n"
            f"Kitaptan en benzer paragraflar:\n{metinler}")
    j = yerel_model.sohbet(HAKEM_MODELI, SISTEM, soru, {"gerekce": {"type": "string"},
                                                       "karar": {"type": "string", "enum": list(KARARLAR)}},
                           num_predict=220, num_ctx=6144)
    if j is None or j.get("karar") not in KARARLAR:
        return {"karar": "?", "gerekce": ""}
    return {"karar": j["karar"], "gerekce": j.get("gerekce", "")}


Gomucu = Callable[[list[str]], np.ndarray]
Hakem = Callable[[Cikti, list[Blok]], dict]


def analiz_et(bloklar: list[Blok], ciktilar: list[Cikti], gomucu: Gomucu | None = None,
              hakem: Hakem | None = None, onbellek: dict | None = None, bekci: Bekci | None = None,
              ilerleme: Callable[[str], None] | None = None) -> tuple[list[dict], list[Tespit]]:
    """(çıktı başına kayıt, tespitler). onbellek: hakem cevapları (aynı soru yeniden sorulmaz)."""
    if gomucu is None:
        from .tutarlilik import ollama_gomucu
        gomucu = ollama_gomucu
    if hakem is None:
        hakem = ollama_kapsam_hakemi
        bekci = bekci or Bekci(ilerleme or print)
    onbellek = {} if onbellek is None else onbellek
    yaz = ilerleme or (lambda _m: None)
    paras = paragraflar(bloklar)
    pv = gomucu([b.metin[:1500] for b in paras])
    cv = gomucu([f"{c.ad}. {c.icerik}" for c in ciktilar])
    pv = pv / np.linalg.norm(pv, axis=1, keepdims=True)
    cv = cv / np.linalg.norm(cv, axis=1, keepdims=True)
    benzerlik = cv @ pv.T
    kavramlar = kavram_sayfalari(sorted({k for c in ciktilar for k in c.kavramlar}), bloklar)
    kayit, tespitler = [], []
    for i, c in enumerate(ciktilar):
        sira = np.argsort(-benzerlik[i])[:EN_YAKIN]
        adaylar = [paras[j] for j in sira]
        anahtar = json.dumps([HAKEM_MODELI, c.kod, c.ad, [b.metin[:200] for b in adaylar]], ensure_ascii=False)
        if anahtar not in onbellek:
            if bekci:
                bekci.adim()
            onbellek[anahtar] = hakem(c, adaylar)
        k = onbellek[anahtar]
        eksik = [kv for kv in c.kavramlar if not kavramlar.get(kv)]
        kayit.append({**asdict(c), "karar": k["karar"], "gerekce": k["gerekce"],
                      "sayfalar": [b.sayfa_no for b in adaylar], "basili": [b.basili_sayfa_no for b in adaylar],
                      "benzerlik": [round(float(benzerlik[i][j]), 3) for j in sira], "eksik_kavramlar": eksik})
        if k["karar"] == "karsilanmiyor":
            b = adaylar[0]
            tespitler.append(Tespit(b.sayfa_no, b.blok_no, b.bbox, "mufredat",
                                    f"Öğrenme çıktısı {c.kod} ({c.ad}) kitapta karşılanmıyor olabilir. "
                                    f"En yakın paragraf s. {b.basili_sayfa_no or b.sayfa_no}. Dil modeli (gemma4): {k['gerekce']}",
                                    0.5, b.basili_sayfa_no, alt_tur="cikti_karsilanmiyor", metin_parcasi=c.kod))
        yaz(f"  {c.kod}: {k['karar']}")
    tespitler += kavram_kontrolu(bloklar, ciktilar, kavramlar)
    return kayit, tespitler


TEMA_YOK_ORANI = 0.5  # bir temanın anahtar kavramlarının en az yarısı yoksa tema kitapta yok sayılır
TEMA_YOK_EN_AZ = 3


def kavram_kontrolu(bloklar: list[Blok], ciktilar: list[Cikti],
                    kavramlar: dict[str, list[int]] | None = None) -> list[Tespit]:
    """Ürüne giren müfredat denetimi (K31 eki): programın anahtar kavramları kitabın konu anlatımında geçiyor mu.
    Bir temanın kavramlarının çoğu yoksa kavram kavram değil, tema için tek not verilir (tema kitapta
    işlenmemiş ya da başka bir ciltte: Sosyal Bilgiler 6 "1. Kitap" ilk üç öğrenme alanını kapsıyor)."""
    if kavramlar is None:
        kavramlar = kavram_sayfalari(sorted({k for c in ciktilar for k in c.kavramlar}), bloklar)
    temalar: dict[tuple[int, int], list[Cikti]] = {}
    for c in ciktilar:
        temalar.setdefault((c.sinif, c.tema), []).append(c)
    tespitler, bildirilen = [], set()
    for (sinif, tema), grup in sorted(temalar.items()):
        tema_kavramlari = list(dict.fromkeys(k for c in grup for k in c.kavramlar))
        eksik = [k for k in tema_kavramlari if not kavramlar.get(k)]
        on_ek = grup[0].kod.rsplit(".", 1)[0]
        if len(tema_kavramlari) >= TEMA_YOK_EN_AZ and len(eksik) >= TEMA_YOK_ORANI * len(tema_kavramlari):
            tespitler.append(Tespit(1, 0, (0, 0, 0, 0), "mufredat",
                                    f"Programın {sinif}. sınıf {tema}. tema / öğrenme alanı ({on_ek}.*, {len(grup)} öğrenme "
                                    f"çıktısı) anahtar kavramlarının {len(eksik)}/{len(tema_kavramlari)} tanesi kitapta "
                                    f"geçmiyor: {', '.join(eksik[:8])}{'…' if len(eksik) > 8 else ''}. Bu tema kitapta "
                                    "işlenmemiş ya da başka bir ciltte olabilir.",
                                    1.0, None, alt_tur="tema_yok", metin_parcasi=on_ek))
            bildirilen.update(eksik)
            continue
        for kv in eksik:
            if kv in bildirilen:
                continue
            bildirilen.add(kv)
            sahipler = [c.kod for c in ciktilar if kv in c.kavramlar]
            kapak = yalniz_tanitimda(kv, bloklar)
            yer = (f"yalnız tanıtım/kapak sayfasında geçiyor (PDF s. {', '.join(map(str, kapak))}), konu "
                   f"anlatımında geçmiyor" if kapak else "kitapta geçmiyor")
            tespitler.append(Tespit(kapak[0] if kapak else 1, 0, (0, 0, 0, 0), "mufredat",
                                    f"Programın anahtar kavramı '{kv}' ({', '.join(sahipler)}) {yer}.",
                                    1.0, None, alt_tur="kavram_yok", metin_parcasi=kv))
    return tespitler


PROGRAMLAR = Path(__file__).resolve().parents[2] / "veri" / "programlar"
EN_AZ_ESLESME = 0.5  # programın o sınıf kavramlarının en az yarısı kitapta geçmeli


def program_bul(bloklar: list[Blok], sinif: int | None = None,
                klasor: Path = PROGRAMLAR) -> tuple[Path, int, list[Cikti]] | None:
    """Kitabın öğretim programı: o sınıfın anahtar kavramlarının en çoğu kitapta geçen program (en az yarısı).
    sinif verilmezse kapaktan bulunur; bulunamazsa None (sınıf tahmin edilmez: alt sınıfların genel kavramları
    — "istek", "dayanışma" — her kitapta geçiyor, Sosyal 6 kitabı 4. sınıfa benziyordu). Ders kitabı ile program
    ayrımı belirgin: Biyoloji 9–11 ve Sosyal 6 kendi programlarıyla 0,75–1,0; TDE ve Matematik kitapları
    Biyoloji programıyla 0,05–0,38. TDE programı beceri temelli: çıktı kodu ayrıştırılmıyor, hiç eşleşmez."""
    if sinif is None:
        from .okunabilirlik import hedef_sinifi_bul
        sinif = hedef_sinifi_bul(bloklar)
        if sinif is None:
            return None
    en_iyi, en_iyi_oran = None, EN_AZ_ESLESME
    for yol in sorted(klasor.glob("*_programi.pdf")) if klasor.exists() else []:
        ciktilar = [c for c in program_ciktilari(yol) if c.sinif == sinif]
        kavramlar = sorted({k for c in ciktilar for k in c.kavramlar})
        if not kavramlar:
            continue
        oran = sum(bool(v) for v in kavram_sayfalari(kavramlar, bloklar).values()) / len(kavramlar)
        if oran >= en_iyi_oran:
            en_iyi, en_iyi_oran = (yol, sinif, ciktilar), oran
    return en_iyi


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Müfredat uyumu (K31): programın anahtar kavramları kitapta geçiyor mu")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--program", type=Path, help="Öğretim programı PDF'i (verilmezse veri/programlar'dan bulunur)")
    ap.add_argument("--sinif", type=int, help="Kitabın sınıfı (verilmezse programla birlikte bulunur)")
    ap.add_argument("--temalar", help='Kitabın kapsadığı temalar ("1-3"); verilmezse hepsi')
    ap.add_argument("--kapsam", action="store_true",
                    help="Deneysel: öğrenme çıktısı kapsamını dil modeline de sor (K31: ölçütü geçmedi, ürün değil)")
    arg = ap.parse_args()
    kok = arg.pdf.with_suffix("")
    bloklar = bloklari_yukle(f"{kok}_bloklar.json")
    if arg.program:
        ciktilar = [c for c in program_ciktilari(arg.program) if arg.sinif is None or c.sinif == arg.sinif]
    elif (bulunan := program_bul(bloklar, arg.sinif)) is None:
        sys.exit("Kitaba uyan öğretim programı bulunamadı (veri/programlar).")
    else:
        yol, sinif, ciktilar = bulunan
        print(f"Program: {yol.name}, {sinif}. sınıf")
    if arg.temalar:
        a, _, b = arg.temalar.partition("-")
        ciktilar = [c for c in ciktilar if int(a) <= c.tema <= int(b or a)]
    if arg.kapsam:
        onbellek_yolu = arg.pdf.with_name("mufredat_onbellek.json")
        onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
        try:
            kayit, tespitler = analiz_et(bloklar, ciktilar, onbellek=onbellek, ilerleme=print)
        finally:
            json_kaydet(onbellek, onbellek_yolu)
        json_kaydet(kayit, f"{kok}_mufredat.json")
        for r in kayit:
            print(f"{r['kod']} [{r['karar']}] s.{r['basili'][:3]} {r['ad'][:70]}")
    else:
        tespitler = kavram_kontrolu(bloklar, ciktilar)
    tespitleri_kaydet(tespitler, f"{kok}_mufredat_tespitler.json")
    for t in tespitler:
        print("-", t.aciklama)
    print(f"{len(tespitler)} tespit")


if __name__ == "__main__":
    main()
