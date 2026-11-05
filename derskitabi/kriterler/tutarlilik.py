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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .. import yerel_model
from ..kayit import bloklari_yukle, json_kaydet, tespitleri_kaydet
from ..donanim import Bekci
from ..model import Blok, Tespit
from ..pdf_cikarma import PARAGRAF_ESIGI
from ..satirlar import grup_metni, satir_gruplari
from .okunabilirlik import cumlelere_bol

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
# Karakter konuşması ("Ayşe: …", "Ahmet: …"): sorulardaki öğrenci karakterleri bilerek farklı
# görüşler savunur; kitabın iddiası değildir (K20 tanımı). Biyoloji 10, s.88'de iki karakterin
# sözleri "çelişki" diye işaretlendi. "Not:", "Örnek:" gibi başlıklar konuşma sayılmaz.
_KONUSMA = re.compile(r"^\s*([A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,})\s*:\s")
_KONUSMA_DEGIL = {"Not", "Örnek", "Sonuç", "Tanım", "Uyarı", "Bilgi", "Kaynak", "Cevap", "Açıklama",
                  "Hatırlatma", "Dikkat", "Etkinlik", "Amaç", "Süre", "Adı", "Konu", "Soru", "Yanıt"}


def konusma_mi(metin: str) -> bool:
    m = _KONUSMA.match(metin)
    return bool(m) and m.group(1) not in _KONUSMA_DEGIL
# Etkinlik yönergesi: altındaki cümleler bilerek yanlış olabilir ("doğru ise ✔ yanlış ise X")
_ETKINLIK = re.compile(r"doğru ise|yanlış ise|işaretleyiniz|eşleştiriniz|boşluklara|doğru mu yanlış mı", re.I)
# Doğru/yanlış etkinliği: maddeleri bilerek yanlış yazılır, hiç karşılaştırılmaz (TDE 12 s.257 ve
# Sosyal 6 s.103'teki sahte çelişkiler). Yönerge ya da "Bilgiler D Y" gibi tablo başlığı; aynı tür
# "Evet/Hayır" yargı tabloları da ("yargılar doğru ise “Evet”… işaretleyiniz") yönerge sayılır.
# Yönerge hem "doğru ise/yanlış ise" hem bir işaretleme sözü içermeli: "uyaranın yönüne doğru ise pozitif"
# (Biyoloji 11) yönerge değildir.
_DY_IFADE = re.compile(r"doğru ise|yanlış ise|doğru mu,? yanlış mı|doğru\s*/\s*yanlış", re.I)
_DY_ISARET = re.compile(r"işaretle|yazınız|belirtiniz|koyunuz|[“\"']D[”\"']|✔|✓", re.I)
_DY_BASLIK = re.compile(r"^\s*(?:\w+\s+)?D\s*/?\s*Y(?:\s+\w+)?\s*$")  # "D Y", "Bilgiler D Y", "Özellikler D Y Açıklama"
_YENI_SORU = re.compile(r"^\s*\d{1,2}\s*[.)](?:\s|$)")


def _dogru_yanlis_yonergesi(metin: str) -> bool:
    return bool(_DY_IFADE.search(metin) and _DY_ISARET.search(metin)) or bool(_DY_BASLIK.match(metin))


def dogru_yanlis_suz(tespitler: list[Tespit], bloklar: list[Blok]) -> list[Tespit]:
    """Önceden hesaplanmış sonuçlardan doğru/yanlış etkinliği maddesine dayanan tespitleri çıkarır
    (kural eklenmeden önce hesaplanmış tam kitap sonuçları için)."""
    dy = dogru_yanlis_bloklari(bloklar)
    return [t for t in tespitler
            if (t.sayfa_no, t.blok_no) not in dy and not any(tuple(k) in dy for k in t.ilgili_konumlar)]


def dogru_yanlis_bloklari(bloklar: list[Blok]) -> set[tuple[int, int]]:
    """Doğru/yanlış etkinliğinin maddeleri: yönergeden sonra aynı sayfada, bir sonraki numaralı
    soruya ("4. …") kadar gelen bloklar."""
    sonuc, sayfa = set(), None
    for b in bloklar:
        if b.sayfa_no != sayfa:
            sayfa = None
        if _dogru_yanlis_yonergesi(b.metin):
            sayfa = b.sayfa_no
            continue
        if sayfa is not None:
            if _YENI_SORU.match(b.metin):
                sayfa = None
            else:
                sonuc.add((b.sayfa_no, b.blok_no))
    return sonuc


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


def _baglam(bloklar: list[Blok], k: int, cumle: str, paragraf_metni: str | None = None) -> str:
    """Aynı sayfadaki önceki 3 blok (başlık, yönerge…) ve paragrafın cümle çevresi. Sayfada
    daha yukarıda bir etkinlik yönergesi varsa o da eklenir (Sosyal 6, s.103: yönerge 4 blok
    yukarıdaydı ve bilerek yanlış yazılmış cümle çelişki sanıldı). paragraf_metni: satır blokları
    birleştirildiyse paragrafın tamamı (k paragrafın ilk bloğu)."""
    b = bloklar[k]
    onceki = [x.metin[:150] for x in bloklar[max(0, k - 3):k]
              if x.sayfa_no == b.sayfa_no and x.tur in ("paragraf", "kisa")]
    etkinlik = next((x.metin[:150] for x in reversed(bloklar[:max(0, k - 3)])
                     if x.sayfa_no == b.sayfa_no and _ETKINLIK.search(x.metin)), None)
    if etkinlik:
        onceki.insert(0, "Etkinlik yönergesi: " + etkinlik)
    metin = paragraf_metni or b.metin
    yer = max(0, metin.find(cumle))
    paragraf = metin[max(0, yer - 400):yer + len(cumle) + 200]
    return " | ".join(onceki + [paragraf])


def alinti_haric(bloklar: list[Blok], pdf_yolu=None) -> set:
    """Çelişki aramasının dışında tutulacak alıntı blokları (K29): tiyatro/hikâye replikleri her
    zaman; imzalı alıntılar (şiir, roman parçası) PDF verilirse (yazı biçimleri PDF'ten okunur).
    Alıntı kitabın kendi iddiası değildir (K20 tanımı): TDE 11'de Cimri oyunundaki iki replik
    ("HARPAGON: …") çelişki sanılmıştı."""
    from . import alinti
    bicimler = alinti.blok_bicimleri(pdf_yolu, bloklar) if pdf_yolu and Path(pdf_yolu).exists() else {}
    return set(alinti.alinti_bloklari(bloklar, bicimler))


def bilgi_cumleleri(bloklar: list[Blok], haric: set | None = None) -> list[Cumle]:
    """Paragraflardaki bilgi cümleleri; kitapta aynen tekrar eden cümle bir kez alınır.
    haric: alınmayacak bloklar {(sayfa_no, blok_no)} (alıntılar, alinti_haric()).
    Satır satır bloklara bölünmüş paragraflar birleştirilir (satirlar.py); cümle, başladığı bloğa bağlanır."""
    indeks = {id(b): k for k, b in enumerate(bloklar)}
    haric = (haric or set()) | dogru_yanlis_bloklari(bloklar)
    gorulen, sonuc = set(), []
    for grup in satir_gruplari(bloklar):
        metin, baslar = grup_metni(grup)
        if ((len(grup) == 1 and grup[0].tur != "paragraf") or len(metin.split()) < PARAGRAF_ESIGI
                or konusma_mi(metin) or any((x.sayfa_no, x.blok_no) in haric for x in grup)):
            continue
        for c in cumlelere_bol(metin):
            if bilgi_cumlesi_mi(c) and c not in gorulen:
                gorulen.add(c)
                yer = metin.find(c)
                b = grup[max(i for i, bas in enumerate(baslar) if bas <= max(yer, 0))]
                sonuc.append(Cumle(c, b.sayfa_no, b.blok_no, b.basili_sayfa_no, b.bbox,
                                   _baglam(bloklar, indeks[id(grup[0])], c, metin if len(grup) > 1 else None)))
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


# --- Ollama (ortak istemci: derskitabi/yerel_model.py) ---

def ollama_gomucu(metinler: list[str]) -> np.ndarray:
    yerel_model.yalniz_bu_model(GOMME_MODELI)
    vektorler = []
    for i in range(0, len(metinler), 64):
        vektorler += yerel_model.istek("/api/embed", {"model": GOMME_MODELI,
                                                      "input": metinler[i:i + 64]})["embeddings"]
    V = np.array(vektorler, dtype=np.float32).reshape(len(metinler), -1)
    return V / np.linalg.norm(V, axis=1, keepdims=True)


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
    # Uzunluk sınırı: bir model bir çiftte durmadan açıklama yazdı (7.674 karakter).
    # Hızlı turda kısa bağlam: ekran kartı belleği daha az dolsun (2026-10-20 çökmesi).
    j = yerel_model.sohbet(model, sistem, soru, ozellikler, num_predict=400 if aciklamali else 20,
                           num_ctx=4096 if aciklamali else 2048)
    if j is None:
        return {"karar": "?", "aciklama": ""}
    return {"karar": j["karar"] if j.get("karar") in KARARLAR else "?", "aciklama": j.get("aciklama", "")}


# --- analiz ---

def _konum(c: Cumle) -> str:
    return f"s. {c.basili_sayfa_no or c.sayfa_no}"


def analiz_et(bloklar: list[Blok], gomucu: Gomucu | None = None, hakem: Hakem | None = None,
              kayit: list | None = None, onbellek: dict | None = None,
              ilerleme: Callable[[str], None] | None = None, bekci: Bekci | None = None,
              haric: set | None = None) -> list[Tespit]:
    """kayit verilirse her aday çiftin bütün kararları buraya yazılır (inceleme için).
    haric: karşılaştırılmayacak alıntı blokları (alinti_haric()).
    onbellek: önceki çalıştırmaların hakem cevapları (aynı çift yeniden sorulmaz).
    bekci: gerçek modellerle çalışırken bilgisayarı korur (pil, sıcaklık, mola; donanim.py)."""
    gomucu = gomucu or ollama_gomucu
    if hakem is None:
        hakem = ollama_hakem
        bekci = bekci or Bekci(ilerleme or print)
    onbellek = {} if onbellek is None else onbellek
    yaz = ilerleme or (lambda _m: None)

    hatalar = []

    def sor(model, a, b, aciklamali, baglam=None):
        anahtar = json.dumps([model, aciklamali, a.metin, b.metin] + (list(baglam) if baglam else []),
                             ensure_ascii=False)
        if anahtar not in onbellek:
            if bekci:
                bekci.adim()
            try:
                onbellek[anahtar] = hakem(model, a.metin, b.metin, aciklamali, baglam)
            except RuntimeError as e:
                # Yeniden denemelere rağmen model bu çifte cevap veremedi (çalıştırıcı çöktü):
                # bütün iş durmasın; çift "?" sayılır, önbelleğe yazılmaz (sonra yeniden denenir)
                hatalar.append(f"s.{a.sayfa_no}/s.{b.sayfa_no}: {str(e)[:120]}")
                yaz(f"  ⚠ Model bu çifte cevap veremedi, atlandı ({len(hatalar)}): {str(e)[:100]}")
                return {"karar": "?", "aciklama": ""}
        return onbellek[anahtar]

    cumleler = bilgi_cumleleri(bloklar, haric)
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
    yaz(f"{len(tespitler)} çelişki tespiti ({time.perf_counter() - t:.0f} sn)"
        + (f"; ⚠ {len(hatalar)} çift modele sorulamadı (yeniden çalıştırınca denenecek)" if hatalar else ""))
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
        tespitler = analiz_et(bloklar, kayit=kayit, onbellek=onbellek, ilerleme=lambda m: print(m, flush=True),
                              haric=alinti_haric(bloklar, Path(f"{kok}.pdf")))
    finally:  # yarıda kesilse bile sorulan çiftler kaybolmasın
        json_kaydet(onbellek, onbellek_yolu)
    tespitleri_kaydet(tespitler, f"{kok}_tutarlilik_tespitler.json")
    json_kaydet(kayit, f"{kok}_tutarlilik_adaylar.json")
    for t in sorted(tespitler, key=lambda t: -t.guven_skoru):
        print(f"[{t.guven_skoru}] {t.aciklama[:300]}")


if __name__ == "__main__":
    main()
