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

Kullanım:
    python -m derskitabi.kriterler.mufredat veri/biyoloji9.pdf veri/programlar/biyoloji_programi.pdf --sinif 9
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


@dataclass
class Cikti:
    kod: str
    sinif: int
    tema: int
    ad: str
    icerik: str = ""
    kavramlar: list[str] = field(default_factory=list)


def _sade(metin: str) -> str:
    return " ".join(metin.replace("-\n", "").split())


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


def kavram_sayfalari(kavramlar: list[str], bloklar: list[Blok]) -> dict[str, list[int]]:
    """{kavram: kitapta geçtiği sayfalar}."""
    sayfa_metni = {}
    for b in bloklar:
        sayfa_metni[b.sayfa_no] = sayfa_metni.get(b.sayfa_no, "") + " " + yazim.tr_kucuk(b.metin)
    return {k: [s for s, m in sorted(sayfa_metni.items()) if _kavram_deseni(k).search(m)] for k in kavramlar}


def paragraflar(bloklar: list[Blok]) -> list[Blok]:
    return [b for b in birlesik_bloklar(bloklar) if b.tur == "paragraf" and len(b.metin.split()) >= EN_AZ_KELIME]


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
    for kv, sayfalar in kavramlar.items():
        if not sayfalar:
            sahipler = [c.kod for c in ciktilar if kv in c.kavramlar]
            tespitler.append(Tespit(1, 0, (0, 0, 0, 0), "mufredat",
                                    f"Anahtar kavram '{kv}' ({', '.join(sahipler)}) kitapta geçmiyor.",
                                    1.0, None, alt_tur="kavram_yok", metin_parcasi=kv))
    return kayit, tespitler


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Müfredat uyumu (K31)")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("program", type=Path)
    ap.add_argument("--sinif", type=int, required=True)
    ap.add_argument("--temalar", help='Kitabın kapsadığı temalar ("1-3"); verilmezse hepsi')
    arg = ap.parse_args()
    kok = arg.pdf.with_suffix("")
    bloklar = bloklari_yukle(f"{kok}_bloklar.json")
    ciktilar = [c for c in program_ciktilari(arg.program) if c.sinif == arg.sinif]
    if arg.temalar:
        a, _, b = arg.temalar.partition("-")
        ciktilar = [c for c in ciktilar if int(a) <= c.tema <= int(b or a)]
    onbellek_yolu = arg.pdf.with_name("mufredat_onbellek.json")
    onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
    try:
        kayit, tespitler = analiz_et(bloklar, ciktilar, onbellek=onbellek, ilerleme=print)
    finally:
        json_kaydet(onbellek, onbellek_yolu)
    json_kaydet(kayit, f"{kok}_mufredat.json")
    tespitleri_kaydet(tespitler, f"{kok}_mufredat_tespitler.json")
    for r in kayit:
        print(f"{r['kod']} [{r['karar']}] s.{r['basili'][:3]} {r['ad'][:70]}")
    print(f"{len(tespitler)} tespit")


if __name__ == "__main__":
    main()
