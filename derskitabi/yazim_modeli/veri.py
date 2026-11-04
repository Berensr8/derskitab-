"""Eğitim / geliştirme / değerlendirme dosyalarının kurulması (K33).

Kaynaklar: GECTurk (kural hataları), Vikipedi gerçek hata çiftleri, kitap cümleleri + yapay hata, GECTurk'ün
hatasız cümleleri + yapay hata ve yazım sözlüğü (asimokby) çiftleri. Cümlelerin yaklaşık yarısı hatasız.

Sızıntı önlemleri:
  - Etiketli / kilitli test setlerinin geçtiği sayfalar (±1) eğitime girmez.
  - TDE 10 hiçbir test setinde yok: tamamı eğitim dışı, E1 (alan içi temiz deneme) olur.
  - Vikipedi çiftleri sayfa adına göre bölünür (aynı sayfa iki tarafta olmaz).
  - Kitap cümlelerinden sistemin herhangi bir yazım tespiti geçenler atılır: gerçek bir hata ya da PDF
    okuma parçası "doğru" diye öğretilmesin.

Kullanım:
    python -m derskitabi.yazim_modeli.veri
"""

import glob
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

from ..kayit import bloklari_yukle, tespitleri_yukle
from ..kriterler.okunabilirlik import cumlelere_bol
from ..satirlar import birlesik_bloklar
from . import sentetik
from .etiketler import SINIF_NO, gecturk_sinifi
from .vikipedi import CIFTLER, levenshtein

PROJE = Path(__file__).resolve().parents[2]
CIKTI = PROJE / "veri" / "yazim_modeli"
MODELLER = PROJE / "modeller"
EGITIM_KITAPLARI = ["kitap", "biyoloji9", "biyoloji10", "biyoloji11", "matematik11", "turkdili9", "turkdili11",
                    "turkdili12"]
DENEME_KITABI = "turkdili10"  # hiçbir test setinde yok
TESTSETI = PROJE / "testseti"
AYNI_DUZELTME_EN_FAZLA = 200
BILINEN: set[str] = set()  # kur() doldurur  # Vikipedi'de aynı "yanlış → doğru" çifti (çoğu toplu düzeltme) en fazla bu kadar


def _hash_orani(s: str) -> float:
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def test_sayfalari() -> dict[str, set[int]]:
    """{kitap: eğitim dışı sayfalar}: bütün test / etiket dosyalarındaki sayfa numaraları ±1."""
    sonuc: dict[str, set[int]] = {}

    def gez(x, kitap=None):
        if isinstance(x, dict):
            kitap = x.get("kitap", kitap)
            for k, v in x.items():
                if k == "sayfa_no" and isinstance(v, int) and kitap:
                    sonuc.setdefault(kitap, set()).update({v - 1, v, v + 1})
                else:
                    gez(v, kitap)
        elif isinstance(x, list):
            for v in x:
                gez(v, kitap)

    for yol in TESTSETI.glob("*.json"):
        gez(json.loads(yol.read_text(encoding="utf-8")))
    return sonuc


def bilinen_hatalar() -> set[str]:
    """Etiketli setlerdeki gerçek hatalar ve eklenmiş hatalar: geçtikleri cümle eğitime "doğru" diye girmesin
    (ör. "sorumluklar" kitapta 3 kez geçtiği için sistem onu terim sayıyor, işaretlemiyor)."""
    sonuc = set()
    for yol in TESTSETI.glob("yazim_*.json"):
        d = json.loads(yol.read_text(encoding="utf-8"))
        d = d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
        for o in d:
            if o.get("etiket") == "gercek" or "aranan" in o:
                sonuc.update(w.strip(sentetik._NOKTALAMA) for w in str(o.get("parca") or o.get("aranan")).split())
    return {w for w in sonuc if len(w) >= 4}


def kitap_cumleleri(kitap: str, haric: set[int]) -> list[tuple[int, list[str]]]:
    """[(sayfa, kelimeler)]: paragraf ve kısa bloklardan 5–60 kelimelik cümleler, tespit geçmeyenler."""
    bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
    tespit_yolu = PROJE / "veri" / f"{kitap}_yazim_tespitler.json"
    isaretli: dict[tuple[int, int], set[str]] = {}
    if tespit_yolu.exists():
        for t in tespitleri_yukle(tespit_yolu):
            isaretli.setdefault((t.sayfa_no, t.blok_no), set()).update((t.metin_parcasi or "").split())
    cumleler = []
    for b in birlesik_bloklar(bloklar):
        if b.sayfa_no in haric or b.tur not in ("paragraf", "kisa"):
            continue
        kotu = isaretli.get((b.sayfa_no, b.blok_no), set()) | BILINEN
        for c in cumlelere_bol(b.metin):
            k = c.split()
            if not 5 <= len(k) <= 60 or any(w.strip(sentetik._NOKTALAMA) in kotu for w in k):
                continue
            if sum(ch.isalpha() for ch in c) < 0.6 * len(c):  # tablo, formül
                continue
            cumleler.append((b.sayfa_no, k))
    return cumleler


def gecturk(bolum: str) -> list[dict]:
    import pyarrow.parquet as pq  # yalnız veri hazırlamada (eğitim sürecinde torch'tan önce yüklenmesin)
    yol = glob.glob(str(MODELLER / "GGLab__GECTurk" / "data" / f"{bolum}-*.parquet"))[0]
    return [{"kaynak": f"gecturk_{bolum}", "kelimeler": r["tokens"],
             "etiketler": [gecturk_sinifi(e) for e in r["labels"]]} for r in pq.read_table(yol).to_pylist()]


_SAPKASIZ = str.maketrans("âîûÂÎÛ", "aiuAIU")


def _sapka(k: str) -> int:
    return sum(h in "âîûÂÎÛ" for h in k)


def vikipedi_ornekleri(denetciler=None) -> dict[str, list[dict]]:
    """Vikipedi çiftleri sayfa adına göre egitim / gelistirme / test. HARF düzeltmesinde düzeltilmiş kelime
    iki araca da yabancıysa (özel ad, yabancı kelime) ve büyük harfle başlıyorsa örnek atılır."""
    bolumler = {"egitim": [], "gelistirme": [], "test": []}
    if not CIFTLER.exists():
        return bolumler
    from ..kriterler.yazim import _gecerli
    ayni = Counter()
    for s in open(CIFTLER, encoding="utf-8"):
        o = json.loads(s)
        etiket = list(o["etiketler"])
        for i, d in o.get("duzeltmeler", {}).items():
            i = int(i)
            w = sentetik._ayir(o["kelimeler"][i])[1]
            v = sentetik._ayir(d)[1]
            anahtar = (w.lower(), v.lower())
            ayni[anahtar] += 1
            if ayni[anahtar] > AYNI_DUZELTME_EN_FAZLA:
                etiket = None
                break
            if (etiket[i] == SINIF_NO["HARF"] and denetciler and v[:1].isupper()
                    and not any(_gecerli(dn, v) for dn in denetciler)):
                etiket = None
                break
            # Vikipedi'de büyük/küçük harf değişikliği çoğunlukla üslup ("Finali" → "finali"); şapka da iki
            # yönde düzeltiliyor ("resmi" → "resmî", "azamî" → "azami"): şapkayı kaldıran düzeltme atılır
            if etiket[i] == SINIF_NO["BUYUK_KUCUK"] or (
                    w.translate(_SAPKASIZ) == v.translate(_SAPKASIZ) and _sapka(v) < _sapka(w)):
                etiket = None
                break
        if etiket is None:
            continue
        o["etiketler"] = etiket
        h = _hash_orani(o["sayfa"])
        bolum = "test" if h < 0.10 else "gelistirme" if h < 0.15 else "egitim"
        bolumler[bolum].append({"kaynak": "vikipedi", "kelimeler": o["kelimeler"], "etiketler": etiket,
                                "sayfa": o["sayfa"]})
    return bolumler


def sozluk_ciftleri(sozcukler: set[str], denetciler) -> dict[str, list[str]]:
    """Yazım sözlüğünden {doğru: [yanlışlar]}: yalnız bizim cümlelerde geçen doğru kelimeler; ikisi de harf,
    küçük harf, ≤ 2 harf farkı; doğru kelime araçlardan birine göre geçerli, yanlış ikisine göre de geçersiz."""
    from ..kriterler.yazim import _gecerli
    yollar = sorted((MODELLER / "asimokby__Turkish-Spelling-Dictionary").glob("*.csv"))
    sonuc: dict[str, list[str]] = {}
    for yol in yollar:
        for satir in open(yol, encoding="utf-8").read().splitlines()[1:]:
            if satir.count(",") != 1:
                continue
            w, v = satir.split(",")
            if v not in sozcukler or w == v or not (w.isalpha() and v.isalpha() and w.islower() and v.islower()):
                continue
            if len(v) < 4 or levenshtein(w, v) > 2:
                continue
            sonuc.setdefault(v, []).append(w)
    temiz = {}
    for v, ws in sonuc.items():
        if not any(_gecerli(d, v) for d in denetciler):
            continue
        ws = [w for w in set(ws) if not any(_gecerli(d, w) for d in denetciler)]
        if ws:
            temiz[v] = ws
    return temiz


def yapay(cumleler: list[list[str]], r: random.Random, kaynak: str, sozluk: dict[str, list[str]] | None = None,
          hatali_orani: float = 0.5) -> list[dict]:
    """Cümlelerin hatali_orani kadarına hata eklenir (bir kısmında sözlükten gerçek yanlış yazım), kalanı hatasız."""
    out = []
    for k in cumleler:
        if r.random() >= hatali_orani:
            out.append({"kaynak": kaynak, "kelimeler": k, "etiketler": [0] * len(k)})
            continue
        if sozluk and r.random() < 0.25:
            yerler = [i for i, w in enumerate(k) if sentetik._ayir(w)[1] in sozluk]
            if yerler:
                i = r.choice(yerler)
                bas, g, son = sentetik._ayir(k[i])
                k2, e = list(k), [0] * len(k)
                k2[i], e[i] = bas + r.choice(sozluk[g]) + son, SINIF_NO["HARF"]
                out.append({"kaynak": kaynak + "_sozluk", "kelimeler": k2, "etiketler": e})
                continue
        o = sentetik.hata_ekle(k, r, 3)
        if o:
            out.append({"kaynak": kaynak, "kelimeler": o[0], "etiketler": o[1]})
        else:
            out.append({"kaynak": kaynak, "kelimeler": k, "etiketler": [0] * len(k)})
    return out


def yaz(ornekler: list[dict], ad: str) -> None:
    with open(CIKTI / f"{ad}.jsonl", "w", encoding="utf-8") as c:
        for o in ornekler:
            c.write(json.dumps(o, ensure_ascii=False) + "\n")


def kur(tohum: int = 33, ilerleme=print) -> dict:
    global BILINEN
    BILINEN = bilinen_hatalar()
    CIKTI.mkdir(parents=True, exist_ok=True)
    r = random.Random(tohum)
    from ..kriterler.yazim import varsayilan_denetciler
    denetciler = varsayilan_denetciler()
    haric = test_sayfalari()
    ilerleme("Eğitim dışı sayfalar: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(haric.items())))

    kitap_egitim, kitap_gelistirme = [], []
    for kitap in EGITIM_KITAPLARI:
        cs = kitap_cumleleri(kitap, haric.get(kitap, set()))
        for sayfa, k in cs:
            (kitap_gelistirme if _hash_orani(f"{kitap}:{sayfa}") < 0.05 else kitap_egitim).append(k)
        ilerleme(f"  {kitap}: {len(cs)} cümle")
    deneme = [k for _, k in kitap_cumleleri(DENEME_KITABI, set())]
    ilerleme(f"  {DENEME_KITABI} (E1, eğitim dışı): {len(deneme)} cümle")

    gt_egitim, gt_gelistirme = gecturk("train"), gecturk("dev")
    gt_temiz = [o["kelimeler"] for o in gt_egitim if not any(o["etiketler"])]
    sozcukler = {sentetik._ayir(w)[1] for k in kitap_egitim + gt_temiz for w in k}
    sozluk = sozluk_ciftleri(sozcukler, denetciler)
    ilerleme(f"Yazım sözlüğü: {len(sozluk)} doğru kelime için {sum(map(len, sozluk.values()))} yanlış yazım")
    viki = vikipedi_ornekleri(denetciler)
    ilerleme("Vikipedi: " + ", ".join(f"{k} {len(v)}" for k, v in viki.items()))

    egitim = (gt_egitim
              + yapay(kitap_egitim, r, "kitap") + yapay(kitap_egitim, r, "kitap")  # her cümle iki kez, farklı hatalar
              + yapay(gt_temiz, r, "gecturk_yapay", sozluk, hatali_orani=0.7)
              + viki["egitim"] * 2)  # gerçek hatalar iki kat ağırlık
    r.shuffle(egitim)
    gelistirme = (r.sample(gt_gelistirme, min(3000, len(gt_gelistirme))) + yapay(kitap_gelistirme, r, "kitap")
                  + viki["gelistirme"])
    r.shuffle(gelistirme)
    yaz(egitim, "egitim")
    yaz(gelistirme, "gelistirme")
    yaz(yapay(deneme, random.Random(999), "tde10"), "e1_tde10")
    yaz(gecturk("test"), "e2_gecturk_test")
    yaz(gecturk("movie_reviews"), "e2_film")
    yaz(viki["test"], "e3_vikipedi")
    say = {ad: Counter(o["kaynak"] for o in v) for ad, v in (("egitim", egitim), ("gelistirme", gelistirme))}
    sinif = Counter(e for o in egitim for e in o["etiketler"])
    ozet = {"egitim": len(egitim), "gelistirme": len(gelistirme), "e1": len(deneme), "e3": len(viki["test"]),
            "kaynaklar": {k: dict(v) for k, v in say.items()}, "siniflar": dict(sinif)}
    (CIKTI / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    ilerleme(f"Veri: {json.dumps(ozet, ensure_ascii=False)}")
    return ozet


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    kur(ilerleme=lambda m: print(m, flush=True))
