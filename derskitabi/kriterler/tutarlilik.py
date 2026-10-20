"""Bilgi tutarsızlığı kriteri (Faz 1, adım 4): kitabın kendi içindeki çelişkiler.

Girdi : Blok listesi (yalnız "paragraf" türü)
Çıktı : Tespit listesi (kriter="tutarlilik"); her tespit iki cümleyi gösterir
        (bulunduğu yer + ilgili_konumlar).

Üç adım (K16, K21, K22):
  1. Bilgi cümleleri bge-m3 ile vektöre çevrilir; anlamca çok benzeyen cümle çiftleri
     aday seçilir (benzerlik ≥ 0,70 ve en yakın 3 komşu).
  2. gemma4 her aday çifte yalnız "çelişki / uyumlu / ilgisiz" der (hızlı ön eleme).
  3. "Çelişki" denen çiftlere gemma4 ve Turkish-Gemma ayrı ayrı açıklamalı karar yazar;
     ikisi de çelişki derse güven 1,0, biri derse 0,5. Bu turda modeller her cümlenin
     geçtiği yeri de görür (aynı sayfadaki önceki bloklar + paragraf): cümle tek başına
     çoğu zaman neyi anlattığını söylemiyor ("Kışlar ılıktır" — hangi iklim?).

Modeller Ollama ile yerel çalışır (K17): önce `ollama serve`.

Kullanım:
    python -m derskitabi.kriterler.tutarlilik veri/kitap_bloklar.json [--sayfalar 40-90]
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..kayit import bloklari_yukle, json_kaydet, tespitleri_kaydet
from ..model import Blok, Tespit
from .okunabilirlik import cumlelere_bol

OLLAMA_URL = "http://127.0.0.1:11434"
GOMME_MODELI = "bge-m3"
HAKEM_MODELI = "gemma4:12b-it-qat"
IKINCI_GORUS_MODELI = "hf.co/ytu-ce-cosmos/Turkish-Gemma-9b-T1-GGUF:Q4_K_M"
BENZERLIK_ESIGI = 0.70  # K21
KOMSU_SAYISI = 3  # K21
MIN_KELIME = 6

# Bir metin listesini satırları birim uzunlukta vektör matrisine çeviren fonksiyon
Gomucu = Callable[[list[str]], np.ndarray]
# (model, cümle 1, cümle 2, açıklamalı mı, (bağlam 1, bağlam 2) ya da None)
#   -> {"karar": ..., "aciklama": ...}
Hakem = Callable[[str, str, str, bool, tuple[str, str] | None], dict]

KARARLAR = ("celiski", "uyumlu", "ilgisiz")
SISTEM = """Sen bir ders kitabı editörüsün. Aynı ders kitabının farklı sayfalarından alınmış iki cümleyi karşılaştırıyorsun.
Görevin: iki cümle arasında bir BİLGİ ÇELİŞKİSİ var mı, yani ikisi aynı anda doğru olamaz mı?
- "celiski": aynı konu hakkında birbiriyle bağdaşmayan bilgi veriyorlar (farklı tarih, sayı, isim, "en/ilk" iddiası vb.).
- "uyumlu": aynı konudalar ve birbiriyle bağdaşıyorlar. Yuvarlanmış sayı, farklı zamana ait bilgi, farklı şeyler için yapılan "ilk/en" iddiaları ve aynı bilginin başka anlatımı çelişki DEĞİLDİR.
- "ilgisiz": farklı konular hakkındalar.
Kendi genel bilgini kullanma: hangi cümlenin doğru olduğunu değil, yalnız iki cümlenin birbiriyle çelişip çelişmediğini değerlendir."""
_BAGLAMLI = """
Her cümlenin geçtiği yer de verildi (aynı sayfadaki önceki bloklar ve cümlenin paragrafı). Cümlelerin neyi anlattığını (hangi ülke, iklim, dönem, olay vb.) buradan anla; farklı şeyleri anlatıyorlarsa çelişki değildir.
Cümle bir etkinlik ya da soru içindeyse (ör. "doğru ise ✔ yanlış ise X" etkinliği) kitabın kendi iddiası olmayabilir; bu durumda çelişki sayma."""
_ACIKLAMALI = "\nÖnce kısa bir Türkçe açıklama yaz (en fazla üç cümle), sonra kararını ver."
_YALNIZ_KARAR = "\nYalnız kararını ver."

# Okura yönelik yönerge ve etkinlik cümleleri bilgi taşımaz ("…tartışınız.",
# "Hazırladığınız ürün … değerlendirilecektir.")
_YONERGE = re.compile(r"[ıiuü]n[ıiuü]z")
# Test şıkkı: "C) Dağlar genellikle denize paralel uzanmaktadır." kitabın iddiası değil
_SIK = re.compile(r"^\s*[A-EİI]\s*\)")
# Etkinlik yönergesi: altındaki cümleler bilerek yanlış olabilir ("doğru ise ✔ yanlış ise X")
_ETKINLIK = re.compile(r"doğru ise|yanlış ise|işaretleyiniz|eşleştiriniz|boşluklara|doğru mu yanlış mı", re.I)


@dataclass
class Cumle:
    metin: str
    sayfa_no: int
    blok_no: int
    basili_sayfa_no: str | None
    bbox: tuple
    baglam: str = ""  # geçtiği yer: aynı sayfadaki önceki bloklar + paragraf (kısaltılmış)


def bilgi_cumlesi_mi(c: str) -> bool:
    k = c.split()
    uzun_kucuk = [w for w in k if len(w) >= 4 and w[:1].islower()]
    return (len(k) >= MIN_KELIME
            and len(uzun_kucuk) >= 3  # harf aralıklı etiketler: "T Ü R K İ Y E", "K a f k a s"
            and sum(map(len, k)) / len(k) >= 3.5
            and not c.startswith("Görsel")
            and not _SIK.match(c)
            and not c.rstrip().endswith("?")
            and not any(_YONERGE.search(w.lower()) for w in k))


def _baglam(bloklar: list[Blok], k: int, cumle: str) -> str:
    """Aynı sayfadaki önceki 3 blok (başlık, yönerge…) ve paragrafın cümle çevresi. Sayfada
    daha yukarıda bir etkinlik yönergesi varsa o da eklenir (Sosyal 6, s.103: yönerge 4 blok
    yukarıdaydı ve bilerek yanlış yazılmış cümle çelişki sanıldı)."""
    b = bloklar[k]
    onceki = [x.metin[:150] for x in bloklar[max(0, k - 3):k]
              if x.sayfa_no == b.sayfa_no and x.tur in ("paragraf", "kisa")]
    etkinlik = next((x.metin[:150] for x in reversed(bloklar[:max(0, k - 3)])
                     if x.sayfa_no == b.sayfa_no and _ETKINLIK.search(x.metin)), None)
    if etkinlik:
        onceki.insert(0, "Etkinlik yönergesi: " + etkinlik)
    yer = max(0, b.metin.find(cumle))
    paragraf = b.metin[max(0, yer - 400):yer + len(cumle) + 200]
    return " | ".join(onceki + [paragraf])


def bilgi_cumleleri(bloklar: list[Blok]) -> list[Cumle]:
    """Paragraflardaki bilgi cümleleri; kitapta aynen tekrar eden cümle bir kez alınır."""
    gorulen, sonuc = set(), []
    for k, b in enumerate(bloklar):
        if b.tur != "paragraf":
            continue
        for c in cumlelere_bol(b.metin):
            if bilgi_cumlesi_mi(c) and c not in gorulen:
                gorulen.add(c)
                sonuc.append(Cumle(c, b.sayfa_no, b.blok_no, b.basili_sayfa_no, b.bbox,
                                   _baglam(bloklar, k, c)))
    return sonuc


def _sade(c: str) -> str:
    return re.sub(r"\W+", " ", c.lower()).strip()


def aday_ciftler(cumleler: list[Cumle], vektorler: np.ndarray) -> list[tuple[int, int, float]]:
    """(i, j, benzerlik) listesi, i < j; en benzerden başlayarak (K21)."""
    S = vektorler @ vektorler.T
    np.fill_diagonal(S, -1.0)
    komsular = np.argsort(-S, axis=1)[:, :KOMSU_SAYISI]
    ciftler = {}
    for i, satir in enumerate(komsular):
        for j in satir:
            a, b = cumleler[i], cumleler[j]
            if S[i, j] < BENZERLIK_ESIGI or (a.sayfa_no, a.blok_no) == (b.sayfa_no, b.blok_no):
                continue
            sa, sb = _sade(a.metin), _sade(b.metin)
            if sa in sb or sb in sa:  # biri diğerinin aynısı/parçası: çelişemez
                continue
            ciftler[(min(i, j), max(i, j))] = float(S[i, j])
    return sorted(((i, j, s) for (i, j), s in ciftler.items()), key=lambda x: -x[2])


# --- Ollama ---

def _istek(yol: str, govde: dict) -> dict:
    r = urllib.request.Request(OLLAMA_URL + yol, json.dumps(govde).encode("utf-8"),
                               {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=300) as cevap:
            return json.loads(cevap.read())
    except urllib.error.URLError as e:
        if isinstance(e, urllib.error.HTTPError):
            raise RuntimeError(f"Ollama hatası ({govde.get('model')}): {e.read().decode(errors='ignore')}") from e
        raise RuntimeError("Ollama'ya bağlanılamadı. Önce `ollama serve` çalıştırın.") from e


def ollama_gomucu(metinler: list[str]) -> np.ndarray:
    vektorler = []
    for i in range(0, len(metinler), 64):
        vektorler += _istek("/api/embed", {"model": GOMME_MODELI, "input": metinler[i:i + 64]})["embeddings"]
    V = np.array(vektorler, dtype=np.float32).reshape(len(metinler), -1)
    return V / np.linalg.norm(V, axis=1, keepdims=True)


_DUSUNME_DESTEKLI: dict[str, bool] = {}


def ollama_hakem(model: str, a: str, b: str, aciklamali: bool,
                 baglam: tuple[str, str] | None = None) -> dict:
    ozellikler = {"karar": {"type": "string", "enum": list(KARARLAR)}}
    if aciklamali:  # açıklama önce yazılır: model kararını gerekçesinden sonra verir
        ozellikler = {"aciklama": {"type": "string"}, **ozellikler}
    soru = f"Cümle 1: {a}\nCümle 2: {b}"
    if baglam:
        soru = (f"Cümle 1: {a}\nCümle 1'in geçtiği yer: {baglam[0]}\n\n"
                f"Cümle 2: {b}\nCümle 2'nin geçtiği yer: {baglam[1]}")
    sistem = SISTEM + (_BAGLAMLI if baglam else "") + (_ACIKLAMALI if aciklamali else _YALNIZ_KARAR)
    govde = {"model": model, "stream": False,
             "format": {"type": "object", "properties": ozellikler, "required": list(ozellikler)},
             # Uzunluk sınırı: bir model bir çiftte durmadan açıklama yazdı (7.674 karakter)
             "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 400 if aciklamali else 20},
             "messages": [{"role": "system", "content": sistem}, {"role": "user", "content": soru}]}
    if _DUSUNME_DESTEKLI.get(model, True):
        try:
            cevap = _istek("/api/chat", {**govde, "think": False})
        except RuntimeError as e:
            if "think" not in str(e):
                raise
            _DUSUNME_DESTEKLI[model] = False  # model "düşünme" ayarını desteklemiyor
            cevap = _istek("/api/chat", govde)
    else:
        cevap = _istek("/api/chat", govde)
    icerik = re.sub(r"<think>.*?</think>", "", cevap["message"]["content"], flags=re.S)
    try:
        j = json.loads(icerik)
        return {"karar": j["karar"] if j.get("karar") in KARARLAR else "?", "aciklama": j.get("aciklama", "")}
    except json.JSONDecodeError:
        return {"karar": "?", "aciklama": icerik[:300]}


# --- analiz ---

def _konum(c: Cumle) -> str:
    return f"s. {c.basili_sayfa_no or c.sayfa_no}"


def analiz_et(bloklar: list[Blok], gomucu: Gomucu | None = None, hakem: Hakem | None = None,
              kayit: list | None = None, onbellek: dict | None = None,
              ilerleme: Callable[[str], None] | None = None) -> list[Tespit]:
    """kayit verilirse her aday çiftin bütün kararları buraya yazılır (inceleme için).
    onbellek: önceki çalıştırmaların hakem cevapları (aynı çift yeniden sorulmaz)."""
    gomucu = gomucu or ollama_gomucu
    hakem = hakem or ollama_hakem
    onbellek = {} if onbellek is None else onbellek
    yaz = ilerleme or (lambda _m: None)

    def sor(model, a, b, aciklamali, baglam=None):
        anahtar = json.dumps([model, aciklamali, a.metin, b.metin] + (list(baglam) if baglam else []),
                             ensure_ascii=False)
        if anahtar not in onbellek:
            onbellek[anahtar] = hakem(model, a.metin, b.metin, aciklamali, baglam)
        return onbellek[anahtar]

    cumleler = bilgi_cumleleri(bloklar)
    if len(cumleler) < 2:
        return []
    t = time.perf_counter()
    adaylar = aday_ciftler(cumleler, gomucu([c.metin for c in cumleler]))
    yaz(f"{len(cumleler)} bilgi cümlesi, {len(adaylar)} aday çift ({time.perf_counter() - t:.0f} sn)")

    # 1. tur: hızlı karar (bütün adaylar)
    izler = []
    for n, (i, j, s) in enumerate(adaylar, 1):
        a, b = sorted((cumleler[i], cumleler[j]), key=lambda c: (c.sayfa_no, c.blok_no))
        izler.append({"a": a, "b": b, "benzerlik": round(s, 3),
                      "hizli": sor(HAKEM_MODELI, a, b, False)["karar"]})
        if n % 100 == 0:
            yaz(f"  hızlı karar {n}/{len(adaylar)} ({time.perf_counter() - t:.0f} sn)")
    supheli = [iz for iz in izler if iz["hizli"] == "celiski"]
    yaz(f"Ön eleme: {len(supheli)} çift 'çelişki' dendi")

    # 2. tur: iki modelin açıklamalı kararı (modeller sırayla yüklensin diye model model)
    for model, alan in ((HAKEM_MODELI, "hakem"), (IKINCI_GORUS_MODELI, "ikinci_gorus")):
        for iz in supheli:
            iz[alan] = sor(model, iz["a"], iz["b"], True, (iz["a"].baglam, iz["b"].baglam))

    tespitler = []
    for iz in supheli:
        oylar = [iz[alan]["karar"] == "celiski" for alan in ("hakem", "ikinci_gorus")]
        if not any(oylar):
            continue
        a, b = iz["a"], iz["b"]
        gerekce = (iz["hakem"] if oylar[0] else iz["ikinci_gorus"])["aciklama"]
        kim = "iki model de (gemma4, Turkish-Gemma)" if all(oylar) else (
            "yalnız gemma4" if oylar[0] else "yalnız Turkish-Gemma")
        iz["guven"] = 1.0 if all(oylar) else 0.5  # kayıtta da görünsün (değerlendirme bunu okur)
        tespitler.append(Tespit(
            sayfa_no=a.sayfa_no, blok_no=a.blok_no, bbox=a.bbox, kriter="tutarlilik",
            aciklama=(f"{_konum(a)}: \"{a.metin}\" ile {_konum(b)}: \"{b.metin}\" çelişiyor olabilir "
                      f"({kim}). {gerekce}"),
            guven_skoru=iz["guven"], basili_sayfa_no=a.basili_sayfa_no,
            alt_tur="kitap_ici_celiski", metin_parcasi=a.metin,
            ilgili_konumlar=[(b.sayfa_no, b.blok_no)]))

    if kayit is not None:
        for iz in izler:
            kayit.append({**iz, "a": vars(iz["a"]), "b": vars(iz["b"])})
    yaz(f"{len(tespitler)} çelişki tespiti ({time.perf_counter() - t:.0f} sn)")
    return tespitler


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Bilgi tutarsızlığı kriteri")
    ap.add_argument("bloklar_json", type=Path)
    ap.add_argument("--sayfalar", help='Yalnız bu sayfalar ("40-90"); çelişkiler bu sayfalar arasında aranır')
    arg = ap.parse_args()

    bloklar = bloklari_yukle(arg.bloklar_json)
    if arg.sayfalar:
        from ..gorsellestir import sayfa_araligi_coz
        secili = set(sayfa_araligi_coz(arg.sayfalar, max(b.sayfa_no for b in bloklar)))
        bloklar = [b for b in bloklar if b.sayfa_no in secili]
    kok = arg.bloklar_json.with_name(arg.bloklar_json.stem.removesuffix("_bloklar"))
    onbellek_yolu = Path(f"{kok}_tutarlilik_onbellek.json")
    onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
    kayit = []
    try:
        tespitler = analiz_et(bloklar, kayit=kayit, onbellek=onbellek,
                              ilerleme=lambda m: print(m, flush=True))
    finally:  # yarıda kesilse bile sorulan çiftler kaybolmasın
        json_kaydet(onbellek, onbellek_yolu)
    tespitleri_kaydet(tespitler, f"{kok}_tutarlilik_tespitler.json")
    json_kaydet(kayit, f"{kok}_tutarlilik_adaylar.json")
    for t in sorted(tespitler, key=lambda t: -t.guven_skoru):
        print(f"[{t.guven_skoru}] {t.aciklama[:300]}")


if __name__ == "__main__":
    main()
