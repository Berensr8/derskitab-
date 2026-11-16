"""Sayfa okuma (K48): yerel dil modeli her sayfayı baştan sona okuyup yazım ve noktalama hatası önerir.

K47 taramasında gemma4, ürünün temiz blok metniyle okuduğunda 44 gerçek hatanın 18'ini buldu; 11'ini
kurallar ve morfoloji bulmuyordu (kelimeyle ilgisi olmayan dizgi hataları, kendi başına geçerli ama yanlış
kullanılmış kelimeler, virgül). Bedeli: sayfa başına birkaç aday ve ~15 sn.

İstem, şema, sıcaklık (0) ve süzgeç eşikleri K43/K47 ile aynıdır; AYARLANMAZ (değişirse ISTEM_SURUMU artar,
önbellek yenilenir). Süzgeçler (yalnızca sayfa düzeninden ya da modelin tutarsızlığından gelen sahte adaylar):
  1. kitaptaki = önerilen (boşluk, büyük/küçük harf, kıvrık/düz kesme farkı yok sayılır);
  2. fark yalnız iki nokta üst üste ve/veya satır sonu eklemek (başlık ve form satırları: "Adı Difüzyon");
  3. satır sonu tiresi kalıntısı ("yapısı-" → "yapısı", "spektru-" → "spektrum-");
  4. aynı yer için mevcut sistemin (kural, morfoloji, kesme) zaten bir tespiti var: yeni tespit üretilmez,
     mevcut tespitin açıklamasına "sayfa okuma da işaretledi" notu eklenir (öncelik değişmez).
Ayrıca kitap metninde (sayfanın bloklarında) geçmeyen aday atılır (modelin uydurduğu metin).
Tespit: kriter "yazim", alt_tur "sayfa_okuma", güven 0,5 (alıntı ya da replik içindeyse 0,25). Yazım hakemi
bu tespitlere sorulmaz (model zaten kendisi önerdi).
"""

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from .. import yerel_model
from ..donanim import Bekci
from ..model import Blok, Tespit
from . import alinti
from .yazim import tr_kucuk

MODEL = "gemma4:12b-it-qat"
ISTEM_SURUMU = "k43-k47-v1"
NUM_CTX = 4096
NUM_PREDICT = 1024
AZAMI_KARAKTER = 4000
GUVEN = 0.5
ALINTI_GUVENI = 0.25
ALT_TUR = "sayfa_okuma"
MEVCUT_NOTU = "Sayfa okuma da işaretledi"
SURE_UYARISI = "Kitap başına yaklaşık 1 saat ekler (300 sayfa)."
ONBELLEK_ADI = "sayfa_okuma_onbellek.json"

# K43/K47 ile birebir aynı sistem istemi, soru şablonu ve JSON şeması (testseti/k43_on_kayit.md)
SISTEM = (
    "Sen Türkçe ders kitapları için çalışan bir yazım editörüsün. Bu ders kitabı sayfasında "
    "yazım, noktalama, dizgi ve yanlış kullanılmış kelime hatalarını bul. Eski metin "
    "alıntılarını, şiirleri ve ağız özelliklerini hata sayma. Her hata için kitaptaki hâlini, "
    "önerini ve kısa gerekçeni ver. Emin değilsen yazma. Sayfada hata yoksa boş liste döndür."
)
SORU_SABLONU = """Kitap ve sayfa: {baslik}

Sayfa metni:
{metin}"""
OZELLIKLER = {
    "hatalar": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "kitaptaki": {"type": "string"},
                "onerilen": {"type": "string"},
                "gerekce": {"type": "string"},
            },
            "required": ["kitaptaki", "onerilen", "gerekce"],
        },
    }
}

# (sayfa başlığı, sayfa metni) -> aday listesi; cevap alınamazsa None
Okuyucu = Callable[[str, str], list[dict] | None]
SURZGEC_ADLARI = {
    "kitapta_yok": "kitap metninde geçmiyor (modelin uydurduğu metin)",
    "ayni_metin": "kitaptaki = önerilen",
    "iki_nokta_satir_sonu": "yalnız iki nokta / satır sonu farkı (sayfa düzeni)",
    "satir_sonu_tiresi": "satır sonu tiresi kalıntısı",
    "mevcut_tespit": "mevcut sistem zaten işaretlemiş (nota eklendi)",
    "tekrar": "aynı sayfada aynı aday tekrarı",
}


def sayfa_okuma_varsayilani(kullanici_secimi: bool | None = None) -> bool:
    """Varsayılan durum: kullanıcı açıkça belirtmediyse Ollama ve gemma4 hazırsa True, değilse False."""
    if kullanici_secimi is not None:
        return bool(kullanici_secimi)
    modeller = yerel_model.yuklu_modeller()
    if modeller is None:
        return False
    kok = MODEL.split(":")[0]
    return any(m == MODEL or m.startswith(kok) for m in modeller)


def _norm(metin: str) -> str:
    """Boşluk, büyük/küçük harf ve kıvrık/düz kesme farkı yok sayılır (K43/K47 eşleşme kuralıyla aynı)."""
    m = tr_kucuk(metin or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", "", m)


def parcalara_bol(metin: str, sinir: int = AZAMI_KARAKTER) -> list[str]:
    if len(metin) <= sinir:
        return [metin]
    parcalar, mevcut, uzunluk = [], [], 0
    for paragraf in metin.split("\n\n"):
        ek = len(paragraf) + (2 if mevcut else 0)
        if mevcut and uzunluk + ek > sinir:
            parcalar.append("\n\n".join(mevcut))
            mevcut, uzunluk = [paragraf], len(paragraf)
        else:
            mevcut.append(paragraf)
            uzunluk += ek
    if mevcut:
        parcalar.append("\n\n".join(mevcut))
    return parcalar


def sayfa_metni(sayfa_bloklari: list[Blok]) -> str:
    """Sayfanın blokları okuma sırasıyla (K47 Araç 3 ile aynı birleştirme)."""
    return "\n\n".join(b.metin for b in sayfa_bloklari if b.metin.strip())


def ollama_okuyucu(baslik: str, metin: str) -> list[dict] | None:
    """Sayfayı modele okutur. Cevap bozuksa None; Ollama hatası RuntimeError olarak yükselir."""
    adaylar = []
    for parca in parcalara_bol(metin):
        cevap = yerel_model.sohbet(MODEL, SISTEM, SORU_SABLONU.format(baslik=baslik, metin=parca), OZELLIKLER,
                                   num_predict=NUM_PREDICT, num_ctx=NUM_CTX)
        if cevap is None or not isinstance(cevap.get("hatalar"), list):
            return None
        for h in cevap["hatalar"]:
            if isinstance(h, dict):
                adaylar.append({a: str(h.get(a, "")).strip() for a in ("kitaptaki", "onerilen", "gerekce")})
    return adaylar


# --- süzgeçler -----------------------------------------------------------------------------------

def ayni_mi(kitaptaki: str, onerilen: str) -> bool:
    return _norm(kitaptaki) == _norm(onerilen)


def iki_nokta_satir_sonu_farki_mi(kitaptaki: str, onerilen: str) -> bool:
    """Fark yalnız ':' ve/veya satır sonu eklemekten ibaret (boşluk farkı zaten yok sayılır)."""
    return _norm(kitaptaki.replace(":", "")) == _norm(onerilen.replace(":", ""))


def satir_sonu_tiresi_mi(kitaptaki: str, onerilen: str) -> bool:
    """'yapısı-' → 'yapısı' (tire kalkıyor) ya da 'spektru-' → 'spektrum-' (kelime tamamlanıyor)."""
    k = kitaptaki.strip()
    if not k.endswith(("-", "‐")):
        return False
    kok = _norm(k[:-1])
    return bool(kok) and _norm(onerilen).rstrip("-‐").startswith(kok)


def _eslesir(a: str, b: str) -> bool:
    x, y = _norm(a), _norm(b)
    return len(x) >= 2 and len(y) >= 2 and (x in y or y in x)


def _bulundugu_blok(kitaptaki: str, sayfa_bloklari: list[Blok]) -> Blok | None:
    aranan = _norm(kitaptaki)
    if not aranan:
        return None
    return next((b for b in sayfa_bloklari if aranan in _norm(b.metin)), None)


# --- ana akış ------------------------------------------------------------------------------------

def alintilari_bul(pdf_yolu, bloklar: list[Blok], sayfalar: set[int] | None = None) -> dict:
    """{(sayfa_no, blok_no): sebep}: alıntı ve replik blokları (ürünün alıntı ayırması; yazı biçimleri PDF'ten)."""
    if not pdf_yolu:
        return {}
    kume = {s + i for s in (sayfalar or {b.sayfa_no for b in bloklar}) for i in range(alinti.ALINTI_EN_FAZLA_SAYFA)}
    ilgili = [b for b in bloklar if b.sayfa_no in kume]
    return alinti.alinti_bloklari(ilgili, alinti.blok_bicimleri(pdf_yolu, ilgili))


def _aciklama(kitaptaki: str, onerilen: str, gerekce: str, alintida: bool) -> str:
    metin = f"Yerel dil modeli (gemma4) sayfayı okurken işaretledi: '{kitaptaki}' → '{onerilen}'."
    if gerekce:
        metin += f" Gerekçe: {gerekce}"
        if not metin.endswith((".", "!", "?")):
            metin += "."
    metin += " Bu öneri bir dil modelinden gelir; ölçülmüş isabeti henüz bilinmiyor."
    if alintida:
        metin += (f" {alinti.ALINTI_NOTU}: yazarın kendi yazımı ya da eski yazım olabilir — düşük öncelik.")
    return metin


def uygula(tespitler: list[Tespit], bloklar: list[Blok], sayfalar: set[int] | None = None,
           alintilar: dict | None = None, okuyucu: Okuyucu | None = None, onbellek: dict | None = None,
           ilerleme: Callable[[str], None] | None = None, kitap_adi: str = "Kitap",
           bekci: Bekci | None = None) -> tuple[list[Tespit], Counter]:
    """Sayfaları okutur; (mevcut tespitler [bazılarına not eklenmiş] + sayfa okuma tespitleri, sayaçlar) döner.

    sayfalar: yalnız bu sayfalar okunur (None = hepsi). Girdi liste değişmez. Model cevap veremeyen sayfa
    atlanır (uyarı yazılır, önbelleğe alınmaz); çalışma durmaz."""
    yaz = ilerleme or (lambda _m: None)
    if okuyucu is None:
        okuyucu = ollama_okuyucu
        bekci = bekci or Bekci(yaz)
    onbellek = {} if onbellek is None else onbellek
    alintilar = alintilar or {}
    sayac = Counter()
    sonuc = list(tespitler)
    yeni = []

    sayfa_bloklari = defaultdict(list)
    for b in bloklar:
        if sayfalar is None or b.sayfa_no in sayfalar:
            sayfa_bloklari[b.sayfa_no].append(b)
    sirali = sorted(s for s, bl in sayfa_bloklari.items() if sayfa_metni(bl))

    for i, sno in enumerate(sirali, start=1):
        bl = sayfa_bloklari[sno]
        metin = sayfa_metni(bl)
        anahtar = json.dumps([MODEL, ISTEM_SURUMU, hashlib.sha1(metin.encode("utf-8")).hexdigest()])
        if anahtar in onbellek:
            adaylar = onbellek[anahtar]
            sayac["onbellekten"] += 1
        else:
            if bekci:
                bekci.adim()
            try:
                adaylar = okuyucu(f"{kitap_adi}, PDF s.{sno}", metin)
            except RuntimeError as e:  # model cevap veremedi: sayfa atlanır
                adaylar = None
                yaz(f"  ⚠ Sayfa {sno} okunamadı: {str(e)[:80]}")
            if adaylar is None:
                sayac["atlanan_sayfa"] += 1
                yaz(f"  ⚠ Sayfa {sno}: model geçerli cevap vermedi, sayfa atlandı")
                continue
            onbellek[anahtar] = adaylar
            sayac["model_cagrisi"] += 1
        sayac["okunan_sayfa"] += 1
        sayac["model_adayi"] += len(adaylar)

        mevcut_idx = [j for j, t in enumerate(sonuc[:len(tespitler)]) if t.sayfa_no == sno and t.metin_parcasi]
        gorulen = set()
        for a in adaylar:
            k, o, g = a.get("kitaptaki", "").strip(), a.get("onerilen", "").strip(), a.get("gerekce", "").strip()
            blok = _bulundugu_blok(k, bl)
            if blok is None:
                sayac["kitapta_yok"] += 1
            elif ayni_mi(k, o):
                sayac["ayni_metin"] += 1
            elif iki_nokta_satir_sonu_farki_mi(k, o):
                sayac["iki_nokta_satir_sonu"] += 1
            elif satir_sonu_tiresi_mi(k, o):
                sayac["satir_sonu_tiresi"] += 1
            elif (cakisan := [j for j in mevcut_idx if _eslesir(k, sonuc[j].metin_parcasi)]):
                for j in cakisan:
                    if MEVCUT_NOTU not in sonuc[j].aciklama:
                        sonuc[j] = replace(sonuc[j], aciklama=f"{sonuc[j].aciklama} {MEVCUT_NOTU}: '{k}' → '{o}'.")
                sayac["mevcut_tespit"] += 1
            elif (blok.blok_no, _norm(k)) in gorulen:
                sayac["tekrar"] += 1
            else:
                gorulen.add((blok.blok_no, _norm(k)))
                alintida = (blok.sayfa_no, blok.blok_no) in alintilar
                sayac["alinti_dusuk"] += alintida
                yeni.append(Tespit(sayfa_no=blok.sayfa_no, blok_no=blok.blok_no, bbox=blok.bbox, kriter="yazim",
                                   aciklama=_aciklama(k, o, g, alintida),
                                   guven_skoru=ALINTI_GUVENI if alintida else GUVEN,
                                   basili_sayfa_no=blok.basili_sayfa_no, alt_tur=ALT_TUR, metin_parcasi=k))
                sayac["tespit"] += 1
        if i % 10 == 0:
            yaz(f"  sayfa okuma {i}/{len(sirali)} sayfa, {sayac['tespit']} tespit")

    atilan = ", ".join(f"{SURZGEC_ADLARI[k]} {sayac[k]}" for k in SURZGEC_ADLARI if sayac[k])
    yaz(f"Sayfa okuma: {sayac['okunan_sayfa']} sayfa okundu ({sayac['onbellekten']} önbellekten), "
        f"{sayac['model_adayi']} aday → {sayac['tespit']} tespit"
        + (f"; atılan: {atilan}" if atilan else "")
        + (f"; {sayac['atlanan_sayfa']} sayfa atlandı" if sayac["atlanan_sayfa"] else ""))
    return sonuc + yeni, sayac


def onbellek_yukle(yol: Path) -> dict:
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else {}


def onbellek_kaydet(onbellek: dict, yol: Path) -> None:
    yol.write_text(json.dumps(onbellek, ensure_ascii=False), encoding="utf-8")
