"""Okunabilirlik kriteri: metnin yaş/sınıf seviyesine uygunluğu (Faz 1, adım 2).

Girdi : Blok listesi (yalnızca "paragraf" türündekiler kullanılır, K8)
Çıktı : (1) Kitap özeti: üç formülün kitap geneli değeri ve literatürdeki karşılığı
        (2) Tespit listesi: kitabın kendi içinde belirgin şekilde zor paragraflar (K9)

Formüller:
  Ateşman (1997)         = 198,825 - 40,175 x (hece/kelime) - 2,610 x (kelime/cümle)
  Çetinkaya-Uzun (2010)  = 118,823 - 25,987 x (hece/kelime) - 0,971 x (kelime/cümle)
  Bezirci-Yılmaz (2010)  = karekök( OKS x (H3x0,84 + H4x1,5 + H5x3,5 + H6x26,25) )
     OKS: cümle başına ortalama kelime; Hn: cümle başına ortalama n heceli kelime (H6: 6+)
  Ateşman ve Çetinkaya-Uzun'da düşük puan = zor; Bezirci-Yılmaz'da yüksek değer = zor.

Kullanım:
    python -m derskitabi.kriterler.okunabilirlik veri/kitap_bloklar.json [--sinif 6]
"""

import argparse
import math
import re
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from ..kayit import bloklari_yukle, json_kaydet, tespitleri_kaydet
from ..model import Blok, Tespit

MIN_CUMLE = 3  # Paragraf düzeyinde değerlendirme için en az cümle sayısı (K10)
ZOR_DILIM = 0.10  # Her formülün "en zor" saydığı dilim: kitabın en zor %10'u (K9)
MIN_ADAY = 10  # Bundan az paragrafta dilim hesaplamak anlamsız; yalnızca özet verilir
HEDEF_SINIF_ARAMA_SAYFASI = 5  # Hedef sınıf yalnızca ilk sayfalarda (kapak) aranır (K11)

_UNLULER = set("aeıioöuüâîûAEIİOÖUÜÂÎÛ")

# Sonundaki nokta cümle bitirmeyen kısaltmalar
_KISALTMA = re.compile(r"\b(M\.Ö|M\.S|vb|vs|bkz|bk|örn|Dr|Prof|Doç|yy|sf|s|No)\.")
# Cümle sonu: . ! ? … (ardından tırnak gelebilir) + boşluk + küçük harfle başlamayan devam.
# "6. sınıf" gibi sıra sayıları küçük harfle devam ettiği için cümle sonu sayılmaz.
_CUMLE_SONU = re.compile(
    r"(?:(?<=[.!?…])|(?<=[.!?…][\"”’'»]))\s+(?=[^a-zçğıöşüâîû\s])"
)
# Kelime: harflerden oluşur, kesme işaretinden sonra ek alabilir ("Atatürk’ün").
# Rakamlar kelime sayılmaz (okunuşlarının hece sayısı belirsiz).
_KELIME = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
_HEDEF_SINIF = re.compile(r"\b(\d{1,2})\s*\.?\s*(?:SINIF|Sınıf|sınıf)\b")
_YER_TUTUCU = "\x00"


def hece_sayisi(kelime: str) -> int:
    """Türkçede her hecede tam bir ünlü vardır: hece sayısı = ünlü sayısı."""
    return max(1, sum(harf in _UNLULER for harf in kelime))


def cumlelere_bol(metin: str) -> list[str]:
    korunan = _KISALTMA.sub(lambda m: m.group(0).replace(".", _YER_TUTUCU), metin)
    parcalar = _CUMLE_SONU.split(korunan)
    cumleler = [p.replace(_YER_TUTUCU, ".").strip() for p in parcalar]
    return [c for c in cumleler if _KELIME.search(c)]


def kelimeler(metin: str) -> list[str]:
    return _KELIME.findall(metin)


@dataclass
class Skorlar:
    cumle_sayisi: int
    kelime_sayisi: int
    hece_kelime: float  # kelime başına ortalama hece
    kelime_cumle: float  # cümle başına ortalama kelime
    atesman: float
    cetinkaya_uzun: float
    bezirci_yilmaz: float


def skorla(metin: str) -> Skorlar | None:
    """Bir metnin üç formüle göre skorları; metinde cümle/kelime yoksa None."""
    cumleler = cumlelere_bol(metin)
    cumle_kelimeleri = [kelimeler(c) for c in cumleler]
    tum_kelimeler = [k for ks in cumle_kelimeleri for k in ks]
    if not cumleler or not tum_kelimeler:
        return None

    heceler = [hece_sayisi(k) for k in tum_kelimeler]
    hk = sum(heceler) / len(tum_kelimeler)
    kc = len(tum_kelimeler) / len(cumleler)

    # Bezirci-Yılmaz: cümle başına ortalama 3, 4, 5 ve 6+ heceli kelime sayıları
    h = {n: sum(1 for x in heceler if min(x, 6) == n) / len(cumleler) for n in (3, 4, 5, 6)}
    yod = math.sqrt(kc * (h[3] * 0.84 + h[4] * 1.5 + h[5] * 3.5 + h[6] * 26.25))

    return Skorlar(
        cumle_sayisi=len(cumleler),
        kelime_sayisi=len(tum_kelimeler),
        hece_kelime=hk,
        kelime_cumle=kc,
        atesman=198.825 - 40.175 * hk - 2.610 * kc,
        cetinkaya_uzun=118.823 - 25.987 * hk - 0.971 * kc,
        bezirci_yilmaz=yod,
    )


# --- Literatürdeki yorum tabloları (kitap özeti için) ---

def atesman_duzeyi(skor: float) -> str:
    # Ateşman'ın sınıf karşılığı yok, yalnızca güçlük düzeyi var.
    if skor >= 90:
        return "çok kolay"
    if skor >= 70:
        return "kolay"
    if skor >= 50:
        return "orta güçlükte"
    if skor >= 30:
        return "zor"
    return "çok zor"


def cetinkaya_uzun_duzeyi(skor: float) -> str:
    if skor >= 51:
        return "bağımsız okuma düzeyi (5–7. sınıf)"
    if skor >= 35:
        return "eğitsel okuma düzeyi (8–9. sınıf)"
    return "engelli okuma düzeyi (10–12. sınıf)"


def bezirci_yilmaz_duzeyi(yod: float) -> str:
    if yod <= 8:
        return "ilköğretim (1–8. sınıf)"
    if yod <= 12:
        return "lise (9–12. sınıf)"
    if yod <= 16:
        return "lisans"
    return "akademik"


def hedef_sinifi_bul(bloklar: list[Blok]) -> int | None:
    """Kapak sayfalarındaki "6 SINIF", "5. Sınıf" gibi ifadeden hedef sınıfı bulur (K11)."""
    for b in bloklar:
        if b.sayfa_no > HEDEF_SINIF_ARAMA_SAYFASI:
            break
        eslesme = _HEDEF_SINIF.search(b.metin)
        if eslesme and 1 <= int(eslesme.group(1)) <= 12:
            return int(eslesme.group(1))
    return None


@dataclass
class KitapOzeti:
    hedef_sinif: int | None
    paragraf_sayisi: int  # skor hesaplanabilen paragraf sayısı (özete katılan)
    degerlendirilen_paragraf: int  # MIN_CUMLE ve üzeri cümleli (tespit adayı)
    # Kitap geneli = paragraf skorlarının ortancası (birleştirilmiş metin değil;
    # sonu noktalamasız bloklar birleşince sözde uzun cümleler oluşuyor)
    atesman: float
    cetinkaya_uzun: float
    bezirci_yilmaz: float
    atesman_duzeyi: str
    cetinkaya_uzun_duzeyi: str
    bezirci_yilmaz_duzeyi: str

    def sozluge(self) -> dict:
        return asdict(self)


def _en_zorlar(adaylar, skor_al, dusuk_zor: bool) -> set[int]:
    """Bir formüle göre en zor ZOR_DILIM'deki adayların indeksleri."""
    sirali = sorted(range(len(adaylar)), key=lambda i: skor_al(adaylar[i][1]),
                    reverse=not dusuk_zor)
    return set(sirali[: math.ceil(len(adaylar) * ZOR_DILIM)])


def _aciklama(s: Skorlar, oy: int, kitap_kc: float) -> str:
    return (
        f"Bu paragraf, 3 formülden {oy} tanesine göre kitabın en zor "
        f"%{ZOR_DILIM * 100:.0f}'luk diliminde. "
        f"Ateşman {s.atesman:.1f} ({atesman_duzeyi(s.atesman)}), "
        f"Çetinkaya-Uzun {s.cetinkaya_uzun:.1f} ({cetinkaya_uzun_duzeyi(s.cetinkaya_uzun)}), "
        f"Bezirci-Yılmaz {s.bezirci_yilmaz:.1f} ({bezirci_yilmaz_duzeyi(s.bezirci_yilmaz)}). "
        f"Cümle başına ortalama {s.kelime_cumle:.1f} kelime (kitap ortancası {kitap_kc:.1f}), "
        f"kelime başına {s.hece_kelime:.2f} hece."
    )


def analiz_et(bloklar: list[Blok], hedef_sinif: int | None = None
              ) -> tuple[KitapOzeti, list[Tespit]]:
    if hedef_sinif is None:
        hedef_sinif = hedef_sinifi_bul(bloklar)

    skorlu = [(b, s) for b in bloklar if b.tur == "paragraf" and (s := skorla(b.metin))]
    if not skorlu:
        raise ValueError("Okunabilirlik için skorlanabilen paragraf yok.")
    adaylar = [(b, s) for b, s in skorlu if s.cumle_sayisi >= MIN_CUMLE]

    ortanca = {alan: statistics.median(getattr(s, alan) for _, s in skorlu)
               for alan in ("atesman", "cetinkaya_uzun", "bezirci_yilmaz", "kelime_cumle")}
    ozet = KitapOzeti(
        hedef_sinif=hedef_sinif,
        paragraf_sayisi=len(skorlu),
        degerlendirilen_paragraf=len(adaylar),
        atesman=round(ortanca["atesman"], 1),
        cetinkaya_uzun=round(ortanca["cetinkaya_uzun"], 1),
        bezirci_yilmaz=round(ortanca["bezirci_yilmaz"], 1),
        atesman_duzeyi=atesman_duzeyi(ortanca["atesman"]),
        cetinkaya_uzun_duzeyi=cetinkaya_uzun_duzeyi(ortanca["cetinkaya_uzun"]),
        bezirci_yilmaz_duzeyi=bezirci_yilmaz_duzeyi(ortanca["bezirci_yilmaz"]),
    )
    if len(adaylar) < MIN_ADAY:
        return ozet, []

    # Her formül kendi "en zor" listesini çıkarır; en az 2 formülün listesindeki
    # paragraflar işaretlenir. Güven skoru = hemfikir formül oranı (K9).
    listeler = [
        _en_zorlar(adaylar, lambda s: s.atesman, dusuk_zor=True),
        _en_zorlar(adaylar, lambda s: s.cetinkaya_uzun, dusuk_zor=True),
        _en_zorlar(adaylar, lambda s: s.bezirci_yilmaz, dusuk_zor=False),
    ]
    tespitler = []
    for i, (b, s) in enumerate(adaylar):
        oy = sum(i in liste for liste in listeler)
        if oy < 2:
            continue
        en_uzun_cumle = max(cumlelere_bol(b.metin), key=lambda c: len(kelimeler(c)))
        tespitler.append(Tespit(
            sayfa_no=b.sayfa_no,
            blok_no=b.blok_no,
            bbox=b.bbox,
            kriter="okunabilirlik",
            aciklama=_aciklama(s, oy, ortanca["kelime_cumle"]),
            guven_skoru=round(oy / 3, 2),
            basili_sayfa_no=b.basili_sayfa_no,
            alt_tur="kitap_ici_zor_paragraf",
            metin_parcasi=en_uzun_cumle,
        ))
    return ozet, tespitler


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Okunabilirlik kriteri")
    ap.add_argument("bloklar_json", type=Path)
    ap.add_argument("--sinif", type=int, help="Hedef sınıf (verilmezse kapaktan bulunur)")
    arg = ap.parse_args()

    ozet, tespitler = analiz_et(bloklari_yukle(arg.bloklar_json), arg.sinif)
    kok = arg.bloklar_json.with_name(arg.bloklar_json.stem.removesuffix("_bloklar"))
    json_kaydet(ozet.sozluge(), f"{kok}_okunabilirlik_ozet.json")
    tespitleri_kaydet(tespitler, f"{kok}_okunabilirlik_tespitler.json")

    hedef = f"{ozet.hedef_sinif}. sınıf" if ozet.hedef_sinif else "bulunamadı (--sinif ile verin)"
    print(f"Hedef sınıf: {hedef}")
    print(f"Paragraf: {ozet.paragraf_sayisi} (özete katılan), "
          f"{ozet.degerlendirilen_paragraf} ({MIN_CUMLE}+ cümle, tespit adayı)")
    print("Kitap geneli (paragraf ortancası):")
    print(f"  Ateşman        {ozet.atesman:>5}  {ozet.atesman_duzeyi}")
    print(f"  Çetinkaya-Uzun {ozet.cetinkaya_uzun:>5}  {ozet.cetinkaya_uzun_duzeyi}")
    print(f"  Bezirci-Yılmaz {ozet.bezirci_yilmaz:>5}  {ozet.bezirci_yilmaz_duzeyi}")
    print(f"Tespit: {len(tespitler)} paragraf "
          f"(3/3 formül: {sum(t.guven_skoru == 1.0 for t in tespitler)})")
    for t in sorted(tespitler, key=lambda t: -t.guven_skoru)[:5]:
        print(f"  [PDF s.{t.sayfa_no} / blok {t.blok_no} / güven {t.guven_skoru}] "
              f"{t.metin_parcasi[:90]}")


if __name__ == "__main__":
    main()
