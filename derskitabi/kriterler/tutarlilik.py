"""Bilgi tutarsızlığı kriteri (Faz 1, adım 4): kitabın kendi içindeki çelişkiler.

Girdi : Blok listesi (yalnız "paragraf" türü)
Çıktı : Tespit listesi (kriter="tutarlilik"); her tespit iki cümleyi gösterir
        (bulunduğu yer + ilgili_konumlar).

Üç adım (K16, K21, K22):
  1. Bilgi cümleleri bge-m3 ile vektöre çevrilir; her cümlenin en yakın 3 komşusu, komşu
     sırasına göre kademeli eşikle aday seçilir (1. komşu ≥ 0,60, 2. ≥ 0,65, 3. ≥ 0,70).
  2. gemma4 her aday çifte yalnız "çelişki / uyumlu / ilgisiz" der (hızlı ön eleme).
  3. "Çelişki" denen çiftlere gemma4 ve Turkish-Gemma ayrı ayrı açıklamalı karar yazar.
     Tespit için gemma4 "çelişki" demeli; Turkish-Gemma da derse güven 1,0, demezse 0,5
     (Turkish-Gemma tek başına tespit üretmez — K22 düzeltmesi). Bu turda modeller her cümlenin
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
from ..donanim import Bekci
from ..model import Blok, Tespit
from .okunabilirlik import cumlelere_bol

OLLAMA_URL = "http://127.0.0.1:11434"
GOMME_MODELI = "bge-m3"
HAKEM_MODELI = "gemma4:12b-it-qat"
IKINCI_GORUS_MODELI = "hf.co/ytu-ce-cosmos/Turkish-Gemma-9b-T1-GGUF:Q4_K_M"
# K21 düzeltmesi: komşu sırasına göre kademeli benzerlik eşiği (1., 2., 3. en yakın komşu).
# Tek bir mutlak eşik (0,70) başka kelimelerle yazılmış çelişkileri kaçırıyordu: geliştirme
# setinde kaynak cümle eklenen cümlenin 1. komşusu olduğu hâlde benzerliği 0,68'di.
KOMSU_ESIKLERI = (0.60, 0.65, 0.70)
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
            # Harf aralıklı etiketleri ("T Ü R K İ Y E", "K a f k a s") asıl ortalama kelime uzunluğu
            # eler; 3 şartı özel isim yoğun cümleleri de eliyordu ("Rusya Federasyonu'nun başkenti
            # St. Petersburg'dur") → 2
            and len(uzun_kucuk) >= 2
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
    """(i, j, benzerlik) listesi, i < j; en benzerden başlayarak (K21, kademeli eşik)."""
    S = vektorler @ vektorler.T
    np.fill_diagonal(S, -1.0)
    komsular = np.argsort(-S, axis=1)[:, :len(KOMSU_ESIKLERI)]
    ciftler = {}
    for i, satir in enumerate(komsular):
        for sira, j in enumerate(satir):
            a, b = cumleler[i], cumleler[j]
            if S[i, j] < KOMSU_ESIKLERI[sira] or (a.sayfa_no, a.blok_no) == (b.sayfa_no, b.blok_no):
                continue
            sa, sb = _sade(a.metin), _sade(b.metin)
            if sa in sb or sb in sa:  # biri diğerinin aynısı/parçası: çelişemez
                continue
            ciftler[(min(i, j), max(i, j))] = float(S[i, j])
    return sorted(((i, j, s) for (i, j), s in ciftler.items()), key=lambda x: -x[2])


# --- Ollama ---

# Uzun çalıştırmalarda Ollama'nın model çalıştırıcısı ara sıra çöküp yeniden yükleniyor
# ("model runner has unexpectedly stopped" — Biyoloji 10 değerlendirmesinde görüldü). Böyle
# geçici hatalarda istek artan beklemeyle yeniden denenir; kalıcı hatalar hemen bildirilir.
YENIDEN_DENEME = (5, 20, 60)  # saniye
_GECICI = ("unexpectedly stopped", "connection", "forcibly closed", "timed out", "EOF", "terminated")


def _istek(yol: str, govde: dict) -> dict:
    for bekleme in (*YENIDEN_DENEME, None):
        r = urllib.request.Request(OLLAMA_URL + yol, json.dumps(govde).encode("utf-8"),
                                   {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=300) as cevap:
                return json.loads(cevap.read())
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            mesaj = e.read().decode(errors="ignore") if isinstance(e, urllib.error.HTTPError) else str(e)
            gecici = not isinstance(e, urllib.error.HTTPError) or any(g in mesaj for g in _GECICI)
            if gecici and bekleme is not None:
                time.sleep(bekleme)
                continue
            if isinstance(e, urllib.error.HTTPError):
                raise RuntimeError(f"Ollama hatası ({govde.get('model')}): {mesaj}") from e
            raise RuntimeError("Ollama'ya bağlanılamadı. Önce `ollama serve` çalıştırın.") from e


_SON_MODEL: list[str | None] = [None]


def _yalniz_bu_model(model: str) -> None:
    """Model değişirken bellekteki diğer modelleri boşaltır. 8 GB ekran kartında gemma4 (~8,5 GB)
    yüklüyken bge-m3 yüklenemeyip çalıştırıcı çöktü ("Load failed", 0xc0000409); her an tek
    model bulunsun."""
    if _SON_MODEL[0] == model:
        return
    try:
        yuklu = [m["name"] for m in _istek_get("/api/ps").get("models", [])]
    except (OSError, ValueError):  # sunucuya ulaşılamazsa boşaltmadan devam (asıl istek hatayı bildirir)
        yuklu = []
    for m in yuklu:
        if m != model and m.split(":latest")[0] != model:
            for yol, govde in (("/api/generate", {"model": m, "keep_alive": 0}),
                               ("/api/embed", {"model": m, "input": "", "keep_alive": 0})):
                try:
                    _istek(yol, govde)
                    break
                except RuntimeError:
                    continue  # gömme modeli /api/generate'i desteklemez
    _SON_MODEL[0] = model


def _istek_get(yol: str) -> dict:
    with urllib.request.urlopen(OLLAMA_URL + yol, timeout=30) as cevap:
        return json.loads(cevap.read())


def ollama_gomucu(metinler: list[str]) -> np.ndarray:
    _yalniz_bu_model(GOMME_MODELI)
    vektorler = []
    for i in range(0, len(metinler), 64):
        vektorler += _istek("/api/embed", {"model": GOMME_MODELI, "input": metinler[i:i + 64]})["embeddings"]
    V = np.array(vektorler, dtype=np.float32).reshape(len(metinler), -1)
    return V / np.linalg.norm(V, axis=1, keepdims=True)


_DUSUNME_DESTEKLI: dict[str, bool] = {}


def ollama_hakem(model: str, a: str, b: str, aciklamali: bool,
                 baglam: tuple[str, str] | None = None) -> dict:
    _yalniz_bu_model(model)
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
             # Hızlı turda kısa bağlam: ekran kartı belleği daha az dolsun (2026-10-20 çökmesi)
             "options": {"temperature": 0, "num_ctx": 4096 if aciklamali else 2048,
                         "num_predict": 400 if aciklamali else 20},
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
              ilerleme: Callable[[str], None] | None = None, bekci: Bekci | None = None) -> list[Tespit]:
    """kayit verilirse her aday çiftin bütün kararları buraya yazılır (inceleme için).
    onbellek: önceki çalıştırmaların hakem cevapları (aynı çift yeniden sorulmaz).
    bekci: gerçek modellerle çalışırken bilgisayarı korur (pil, sıcaklık, mola; donanim.py)."""
    gomucu = gomucu or ollama_gomucu
    if hakem is None:
        hakem = ollama_hakem
        bekci = bekci or Bekci(ilerleme or print)
    onbellek = {} if onbellek is None else onbellek
    yaz = ilerleme or (lambda _m: None)

    def sor(model, a, b, aciklamali, baglam=None):
        anahtar = json.dumps([model, aciklamali, a.metin, b.metin] + (list(baglam) if baglam else []),
                             ensure_ascii=False)
        if anahtar not in onbellek:
            if bekci:
                bekci.adim()
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
        # K22 düzeltmesi: tespit için gemma4 "çelişki" demeli. Geliştirme setinde Turkish-Gemma'nın
        # tek başına "çelişki" dediği 8 çiftin 8'i sahteydi; doğru bulunan 9 çelişkinin 9'unda
        # gemma4 "çelişki" demişti. Turkish-Gemma yalnız güveni artırır.
        if not oylar[0]:
            continue
        a, b = iz["a"], iz["b"]
        gerekce = iz["hakem"]["aciklama"]
        kim = "iki model de (gemma4, Turkish-Gemma)" if all(oylar) else "yalnız gemma4"
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
