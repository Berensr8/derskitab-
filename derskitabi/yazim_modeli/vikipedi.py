"""Türkçe Vikipedi değişiklik geçmişinden gerçek yazım hatası → düzeltme çiftleri (K33).

Üç aşama:
  1. aday   : değişiklik kayıtları dökümünden (stub-meta-history, metinsiz) ana ad alanında, açıklaması
              yazım / imla / typo … içeren, boyutu az değişmiş ve geri alma olmayan değişiklikler seçilir.
  2. fark   : seçilen her değişikliğin önceki sürümle farkı Vikipedi API'sinden alınır (action=compare).
              Kurallara uygun: istekler sırayla, gzip, maxlag ve tanıtıcı User-Agent ile; kaldığı yerden devam eder.
  3. cift   : farktaki değişmiş satırlar viki biçiminden temizlenir, kelime kelime hizalanır. Satırdaki her
              değişiklik küçük bir yazım düzeltmesiyse (≤ 2 harf, şapka, büyük/küçük harf, kesme işareti,
              bitişik ↔ ayrı) satırın eski hâlindeki cümle hatalı kelimeleri etiketlenmiş örnek olur; satırda
              başka türden bir değişiklik varsa (anlam değişikliği) satır bütünüyle atılır.

Kullanım:
    python -m derskitabi.yazim_modeli.vikipedi aday veri/vikipedi/trwiki-latest-stub-meta-history.xml.gz
    python -m derskitabi.yazim_modeli.vikipedi fark --en-fazla 30000 --saat 3
    python -m derskitabi.yazim_modeli.vikipedi cift
"""

import argparse
import difflib
import gzip
import html
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .etiketler import SINIF_NO

KLASOR = Path(__file__).resolve().parents[2] / "veri" / "vikipedi"
ADAYLAR = KLASOR / "adaylar.jsonl"
FARKLAR = KLASOR / "farklar.jsonl"
CIFTLER = KLASOR / "ciftler.jsonl"
API = "https://tr.wikipedia.org/w/api.php"
KIMLIK = "derskitabi-arastirma/0.1 (ders projesi; https://github.com/Berensr8/derskitab-) python-urllib"

_YAZIM_ACIKLAMASI = re.compile(r"yaz[ıi]m|imla|typo|harf hata|b[üu]y[üu]k harf|k[üu][çc][üu]k harf|biti[şs]ik|"
                               r"ayr[ıi] yaz|yaz[ıi]l[ıi][şs]|kesme i[şs]areti|d[üu]zeltme", re.I)
_GUCLU_ACIKLAMA = re.compile(r"yaz[ıi]m|imla|typo|harf hata|yaz[ıi]l[ıi][şs]", re.I)
_GERI_ALMA = re.compile(r"geri al|revert|\brv\b|vandal|eski s[üu]r[üu]m", re.I)
EN_FAZLA_BOYUT_FARKI = 12  # bayt: yazım düzeltmesi sayfanın boyutunu az değiştirir


# 1. Aday değişiklikler ------------------------------------------------------------------------------

def _etiket_degeri(satir: str, ad: str) -> str | None:
    m = re.search(rf"<{ad}>(.*?)</{ad}>", satir)
    return html.unescape(m.group(1)) if m else None


def adaylari_sec(dokum: Path, cikti: Path = ADAYLAR, ilerleme=print) -> int:
    """Döküm satır satır okunur (her XML öğesi kendi satırında): XML ayrıştırıcıdan çok daha hızlı."""
    sayi, sayfa_sayisi = 0, 0
    with gzip.open(dokum, "rt", encoding="utf-8") as g, open(cikti, "w", encoding="utf-8") as c:
        baslik, ns, boyutlar = None, None, {}
        rev = {}
        katkici = False
        for satir in g:
            s = satir.strip()
            if s == "<page>":
                baslik, ns, boyutlar = None, None, {}
                sayfa_sayisi += 1
                if sayfa_sayisi % 200000 == 0:
                    ilerleme(f"  {sayfa_sayisi} sayfa, {sayi} aday")
            elif s.startswith("<title>"):
                baslik = _etiket_degeri(s, "title")
            elif s.startswith("<ns>"):
                ns = _etiket_degeri(s, "ns")
            elif s == "<revision>":
                rev = {}
            elif s == "<contributor>":
                katkici = True
            elif s == "</contributor>":
                katkici = False
            elif katkici:
                if s.startswith("<username>"):
                    rev["kullanici"] = _etiket_degeri(s, "username")
            elif s.startswith("<id>") and "id" not in rev:
                rev["id"] = int(_etiket_degeri(s, "id"))
            elif s.startswith("<parentid>"):
                rev["ust"] = int(_etiket_degeri(s, "parentid"))
            elif s.startswith("<comment>"):
                rev["aciklama"] = _etiket_degeri(s, "comment") or ""
            elif s.startswith("<text") and "bytes=" in s:
                m = re.search(r'bytes="(\d+)"', s)
                rev["boyut"] = int(m.group(1)) if m else None
                rev["silinmis"] = 'deleted="deleted"' in s
            elif s == "</revision>":
                if "id" in rev and rev.get("boyut") is not None:
                    boyutlar[rev["id"]] = rev["boyut"]
                if (ns == "0" and "ust" in rev and not rev.get("silinmis") and rev.get("aciklama")
                        and rev["ust"] in boyutlar and _YAZIM_ACIKLAMASI.search(rev["aciklama"])
                        and not _GERI_ALMA.search(rev["aciklama"])
                        and abs(rev["boyut"] - boyutlar[rev["ust"]]) <= EN_FAZLA_BOYUT_FARKI):
                    kullanici = rev.get("kullanici") or ""
                    c.write(json.dumps({"rev": rev["id"], "ust": rev["ust"], "baslik": baslik,
                                        "aciklama": rev["aciklama"][:200], "fark": rev["boyut"] - boyutlar[rev["ust"]],
                                        "bot": "bot" in kullanici.lower() or "bot:" in rev["aciklama"].lower()},
                                       ensure_ascii=False) + "\n")
                    sayi += 1
    ilerleme(f"Aday: {sayi} değişiklik ({sayfa_sayisi} sayfa tarandı)")
    return sayi


# 2. Farklar ----------------------------------------------------------------------------------------

def _istek(params: dict, deneme: int = 6) -> dict | None:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": 2, "maxlag": 5})
    bekle = 5
    for _ in range(deneme):
        try:
            istek = urllib.request.Request(url, headers={"User-Agent": KIMLIK, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(istek, timeout=60) as y:
                veri = y.read()
                if y.headers.get("Content-Encoding") == "gzip":
                    veri = gzip.decompress(veri)
            j = json.loads(veri)
            if j.get("error", {}).get("code") == "maxlag":
                time.sleep(bekle)
                bekle = min(bekle * 2, 120)
                continue
            return j
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            time.sleep(bekle)
            bekle = min(bekle * 2, 300)
    return None


_SATIR = re.compile(r"<tr>(.*?)</tr>", re.S)
_SILINEN = re.compile(r'<td class="diff-deletedline[^"]*"[^>]*>(.*?)</td>', re.S)
_EKLENEN = re.compile(r'<td class="diff-addedline[^"]*"[^>]*>(.*?)</td>', re.S)


def _duz(h: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", h))


def fark_satirlari(fark_html: str) -> list[tuple[str, str]]:
    """Fark tablosunda aynı satırın eski ve yeni hâli (yalnız değişmiş satırlar)."""
    cift = []
    for tr in _SATIR.findall(fark_html):
        s, e = _SILINEN.search(tr), _EKLENEN.search(tr)
        if s and e:
            cift.append((_duz(s.group(1)), _duz(e.group(1))))
    return cift


KILIT = KLASOR / "fark.kilit"


def farklari_indir(en_fazla: int = 30000, saat: float = 3.0, tohum: int = 33, ilerleme=print) -> int:
    """Aynı anda tek indirici çalışır (kilit dosyasında süreç numarası; gece betiği bekler)."""
    KILIT.write_text(str(os.getpid()))
    try:
        return _farklari_indir(en_fazla, saat, tohum, ilerleme)
    finally:
        KILIT.unlink(missing_ok=True)


def _farklari_indir(en_fazla: int, saat: float, tohum: int, ilerleme) -> int:
    adaylar = [json.loads(s) for s in open(ADAYLAR, encoding="utf-8")]
    random.Random(tohum).shuffle(adaylar)
    # açıklamasında açıkça yazım / imla / typo geçenler önce ("bağlantı düzeltme" gibi genel olanlar sonra)
    adaylar.sort(key=lambda a: not _GUCLU_ACIKLAMA.search(a["aciklama"]))
    adaylar = adaylar[:en_fazla]
    yapilan = set()
    if FARKLAR.exists():
        for s in open(FARKLAR, encoding="utf-8"):
            try:
                yapilan.add(json.loads(s)["rev"])
            except json.JSONDecodeError:
                pass
    bitis = time.time() + saat * 3600
    yeni = 0
    with open(FARKLAR, "a", encoding="utf-8") as c:
        for i, a in enumerate(adaylar):
            if a["rev"] in yapilan:
                continue
            if time.time() > bitis:
                ilerleme(f"Süre doldu: {len(yapilan) + yeni} fark")
                break
            j = _istek({"action": "compare", "fromrev": a["ust"], "torev": a["rev"], "prop": "diff"})
            fark = (j or {}).get("compare", {}).get("body") or ""
            c.write(json.dumps({**a, "satirlar": fark_satirlari(fark)}, ensure_ascii=False) + "\n")
            yeni += 1
            if yeni % 500 == 0:
                c.flush()
                ilerleme(f"  {len(yapilan) + yeni}/{len(adaylar)} fark")
    ilerleme(f"Fark: {len(yapilan) + yeni} değişiklik indirildi ({yeni} yeni)")
    return yeni


# 3. Çiftler ----------------------------------------------------------------------------------------

def temizle(s: str) -> str:
    """Viki biçimini düz metne yaklaştırır (kaynakça, şablon, bağlantı, kalın/italik, tablo işaretleri)."""
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", " ", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    for _ in range(5):
        s2 = re.sub(r"\{\{[^{}]*\}\}", " ", s)
        if s2 == s:
            break
        s = s2
    s = re.sub(r"\[\[(?:Dosya|Resim|File|Image|Kategori|Category):[^\]]*\]\]", " ", s, flags=re.I)
    s = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", s)
    s = re.sub(r"https?://\S+", " ", s)
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"^[*#:;=|!{}]+", " ", s.strip())
    s = re.sub(r"=+\s*$", " ", s)
    return " ".join(s.split())


_NOKTALAMA = "\"'“”‘’«»()[]{}.,;:!?…-–—/"


def kelimeler(s: str) -> list[str]:
    """Boşlukla ayrılmış kelimeler, noktalama bitişik (GECTurk ile aynı biçim: "başlıyor.", "okul,")."""
    return s.split()


def cekirdek(k: str) -> tuple[str, str, str]:
    """(baştaki noktalama, kelime, sondaki noktalama)."""
    govde = k.strip(_NOKTALAMA)
    if not govde:
        return k, "", ""
    bas = k.index(govde)
    return k[:bas], govde, k[bas + len(govde):]


def _harf_mi(k: str) -> bool:
    return bool(re.fullmatch(r"[^\W\d_]+(?:['’][^\W\d_]+)?", k))


def levenshtein(a: str, b: str) -> int:
    onceki = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        simdi = [i]
        for j, cb in enumerate(b, 1):
            simdi.append(min(onceki[j] + 1, simdi[j - 1] + 1, onceki[j - 1] + (ca != cb)))
        onceki = simdi
    return onceki[-1]


def degisiklik_turu(eski: list[str], yeni: list[str]) -> str | None:
    """Bir hizalama bloğu yazım düzeltmesi mi; öyleyse sınıfı. Değilse None (satır atılır)."""
    if len(eski) == 1 and len(yeni) == 1:
        (b1, w, s1), (b2, v, s2) = cekirdek(eski[0]), cekirdek(yeni[0])
        if (b1, s1) != (b2, s2) or not (_harf_mi(w) and _harf_mi(v)) or len(v) < 2:
            return None  # noktalama değişikliği ya da sayı / sembol
        if w.lower() == v.lower():
            return "BUYUK_KUCUK" if w[:1] != v[:1] else None
        if w.replace("'", "").replace("’", "").lower() == v.replace("'", "").replace("’", "").lower():
            return "KURAL_DIGER"  # kesme işareti
        if levenshtein(w.lower(), v.lower()) <= 2 and min(len(w), len(v)) >= 3:
            return "HARF"
        return None
    if 1 <= len(eski) <= 3 and 1 <= len(yeni) <= 3 and len(eski) != len(yeni):
        if "".join(eski).lower() == "".join(yeni).lower() and all(_harf_mi(cekirdek(k)[1]) for k in eski + yeni):
            return "BITISIK_AYRI"
    return None


def _cumleler(k: list[str]) -> list[tuple[int, int]]:
    """Kelime listesini cümlelere böler: (başlangıç, bitiş) aralıkları."""
    sinirlar, bas = [], 0
    for i, t in enumerate(k):
        if t[-1:] in ".!?" and (i + 1 == len(k) or k[i + 1][:1].isupper()):
            sinirlar.append((bas, i + 1))
            bas = i + 1
    if bas < len(k):
        sinirlar.append((bas, len(k)))
    return sinirlar


def satir_ornekleri(eski_satir: str, yeni_satir: str) -> list[dict] | None:
    """Eski satırın cümleleri, hatalı kelimeleri etiketli. Satırda yazım dışı bir değişiklik varsa None."""
    a, b = kelimeler(temizle(eski_satir)), kelimeler(temizle(yeni_satir))
    if not a or a == b:
        return None
    etiket = [0] * len(a)
    duzeltme = {}  # eski kelime sırası → düzeltilmiş hâli (bitişik/ayrıda bloğun tamamı)
    bloklar = [o for o in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes() if o[0] != "equal"]
    if not bloklar or len(bloklar) > 4:
        return None
    for op, i1, i2, j1, j2 in bloklar:
        if op != "replace":
            return None  # eklenen / silinen kelime: anlam değişikliği olabilir
        if i2 - i1 == j2 - j1 > 1:  # yan yana birkaç kelime ayrı ayrı düzeltilmiş ("kisisel gelisim")
            turler = [degisiklik_turu([a[i]], [b[j1 + i - i1]]) for i in range(i1, i2)]
        else:
            turler = [degisiklik_turu(a[i1:i2], b[j1:j2])] * (i2 - i1)
        if None in turler:
            return None
        for i, tur in zip(range(i1, i2), turler):
            etiket[i] = SINIF_NO[tur]
            duzeltme[i] = b[j1 + i - i1] if i2 - i1 == j2 - j1 else " ".join(b[j1:j2])
    ornekler = []
    for c1, c2 in _cumleler(a):
        if not (5 <= c2 - c1 <= 80):
            continue
        ornekler.append({"kelimeler": a[c1:c2], "etiketler": etiket[c1:c2],
                         "duzeltmeler": {str(i - c1): v for i, v in duzeltme.items() if c1 <= i < c2}})
    return ornekler


def ciftleri_cikar(cikti: Path = CIFTLER, ilerleme=print) -> dict:
    """Her değişiklikten hatalı cümleler (en az bir etiketli kelime) ve aynı satırdan en fazla bir hatasız cümle."""
    say = {"degisiklik": 0, "kabul": 0, "hatali_cumle": 0, "hatasiz_cumle": 0}
    with open(cikti, "w", encoding="utf-8") as c:
        for s in open(FARKLAR, encoding="utf-8"):
            try:
                d = json.loads(s)
            except json.JSONDecodeError:  # indirme bir satırı yazarken kesildiyse
                continue
            say["degisiklik"] += 1
            kabul = False
            for eski, yeni in d["satirlar"]:
                ornekler = satir_ornekleri(eski, yeni)
                if not ornekler:
                    continue
                hatasiz_eklendi = False
                for o in ornekler:
                    hatali = any(o["etiketler"])
                    if not hatali and hatasiz_eklendi:
                        continue
                    hatasiz_eklendi |= not hatali
                    say["hatali_cumle" if hatali else "hatasiz_cumle"] += 1
                    kabul |= hatali
                    c.write(json.dumps({"kaynak": "vikipedi", "sayfa": d["baslik"], "rev": d["rev"], "bot": d["bot"],
                                        **o}, ensure_ascii=False) + "\n")
            say["kabul"] += kabul
    ilerleme(f"Çift: {say}")
    return say


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Vikipedi değişiklik geçmişinden yazım hatası çiftleri (K33)")
    alt = ap.add_subparsers(dest="asama", required=True)
    a = alt.add_parser("aday")
    a.add_argument("dokum", type=Path)
    f = alt.add_parser("fark")
    f.add_argument("--en-fazla", type=int, default=30000)
    f.add_argument("--saat", type=float, default=3.0)
    alt.add_parser("cift")
    arg = ap.parse_args()
    yaz = lambda m: print(m, flush=True)  # noqa: E731
    if arg.asama == "aday":
        adaylari_sec(arg.dokum, ilerleme=yaz)
    elif arg.asama == "fark":
        farklari_indir(arg.en_fazla, arg.saat, ilerleme=yaz)
    else:
        ciftleri_cikar(ilerleme=yaz)


if __name__ == "__main__":
    main()
