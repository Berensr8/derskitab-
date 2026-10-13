"""Sistemin gözünden PDF: çıkarma ve analiz sonuçlarını kitabın üzerine çizer.

Girdi : PDF dosyası
Çıktı : <kitap>_isaretli.pdf. Her sayfada:
  - Her blok, türüne göre renkli çerçeve + köşesinde blok numarası
    (yeşil = paragraf, mavi = kısa, kırmızı = bozuk, gri = simge).
    Çerçevenin üzerine gelince: tür, cümleler, kelime/hece sayıları, skorlar.
  - Paragraflarda cümleler sırayla sarı / turkuaz vurgulanır (cümle bölmenin
    nerede yapıldığı görülsün diye).
  - Okunabilirlik tespitleri kalın turuncu çerçeve + açıklama notu.

Kullanım:
    python -m derskitabi.gorsellestir veri/kitap.pdf [--sayfalar 28-35,89] [--sinif 6]

blok_raporu() bilgiyi çizimden bağımsız üretir; ileride etkileşimli bir
görüntüleyici (HTML vb.) aynı fonksiyonu kullanabilir.
"""

import argparse
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf

from .kriterler import okunabilirlik
from .model import Blok, Tespit
from .pdf_cikarma import _OKUMA_AYARLARI, PARAGRAF_ESIGI, bloklari_cikar

RENKLER = {
    "paragraf": (0.0, 0.6, 0.0),
    "kisa": (0.0, 0.35, 0.9),
    "bozuk": (0.9, 0.0, 0.0),
    "simge": (0.55, 0.55, 0.55),
}
CUMLE_RENKLERI = [(1.0, 0.92, 0.3), (0.55, 0.88, 1.0)]  # sarı, turkuaz (sırayla)
TESPIT_RENGI = (1.0, 0.5, 0.0)
ACIKLAMA_FONTU = Path(r"C:\Windows\Fonts\arial.ttf")  # Türkçe harfler için

_TUR_ACIKLAMASI = {
    "paragraf": "Okunabilirlik ve (ileride) yazım + bilgi tutarsızlığı kriterleri analiz eder.",
    "kisa": f"{PARAGRAF_ESIGI} kelimeden az (başlık, etiket, altyazı). "
            "Yalnızca yazım kriteri bakacak (ileride).",
    "bozuk": "Metin okunamıyor ('\ufffd' içeriyor): font Türkçe harfleri bozuk kodlamış. "
             "Hiçbir kriter analiz etmez (OCR Faz 1 dışı).",
    "simge": "Harf veya rakam yok (harita simgesi vb.). Analiz edilmez.",
}


# --- 1. Bilgi katmanı (çizimden bağımsız) ---

def blok_raporu(blok: Blok) -> dict:
    """Bir bloğun sistem tarafından nasıl algılandığı: tür, cümleler, heceler, skorlar."""
    rapor = {"blok_no": blok.blok_no, "tur": blok.tur, "metin": blok.metin,
             "tur_aciklamasi": _TUR_ACIKLAMASI[blok.tur], "cumleler": [], "skorlar": None}
    if blok.tur != "paragraf":
        return rapor
    for c in okunabilirlik.cumlelere_bol(blok.metin):
        kelimeler = okunabilirlik.kelimeler(c)
        rapor["cumleler"].append({
            "metin": c,
            "kelimeler": [(k, okunabilirlik.hece_sayisi(k)) for k in kelimeler],
        })
    skor = okunabilirlik.skorla(blok.metin)
    if skor:
        # Formül hesabının ara adımları (inceleyicide adım adım gösterilir)
        heceler = [h for c in rapor["cumleler"] for _, h in c["kelimeler"]]
        n_cumle, n_kelime = len(rapor["cumleler"]), len(heceler)
        hesap = {
            "cumle": n_cumle,
            "kelime": n_kelime,
            "hece": sum(heceler),
            "hece_kelime": sum(heceler) / n_kelime,
            "kelime_cumle": n_kelime / n_cumle,
            # Bezirci-Yılmaz: cümle başına ortalama n heceli kelime (6 = 6 ve üstü)
            "h": {str(n): sum(1 for h in heceler if min(h, 6) == n) / n_cumle for n in (3, 4, 5, 6)},
        }
        rapor["skorlar"] = {
            "hesap": hesap,
            "atesman": (round(skor.atesman, 1), okunabilirlik.atesman_duzeyi(skor.atesman)),
            "cetinkaya_uzun": (round(skor.cetinkaya_uzun, 1),
                               okunabilirlik.cetinkaya_uzun_duzeyi(skor.cetinkaya_uzun)),
            "bezirci_yilmaz": (round(skor.bezirci_yilmaz, 1),
                               okunabilirlik.bezirci_yilmaz_duzeyi(skor.bezirci_yilmaz)),
            "tespit_adayi": skor.cumle_sayisi >= okunabilirlik.MIN_CUMLE,
        }
    return rapor


def rapor_metni(rapor: dict) -> str:
    """blok_raporu() çıktısını PDF notunda gösterilecek düz metne çevirir."""
    satirlar = [f"Blok {rapor['blok_no']} · tür: {rapor['tur']}", rapor["tur_aciklamasi"]]
    cumleler = rapor["cumleler"]
    if cumleler:
        kelime = sum(len(c["kelimeler"]) for c in cumleler)
        hece = sum(h for c in cumleler for _, h in c["kelimeler"])
        satirlar.append(f"{len(cumleler)} cümle · {kelime} kelime · {hece} hece")
    if rapor["skorlar"]:
        s = rapor["skorlar"]
        satirlar += [
            f"Ateşman {s['atesman'][0]} ({s['atesman'][1]})",
            f"Çetinkaya-Uzun {s['cetinkaya_uzun'][0]} ({s['cetinkaya_uzun'][1]})",
            f"Bezirci-Yılmaz {s['bezirci_yilmaz'][0]} ({s['bezirci_yilmaz'][1]})",
            "Okunabilirlik tespit adayı: " + (
                "evet" if s["tespit_adayi"] else f"hayır ({okunabilirlik.MIN_CUMLE} cümleden az)"),
        ]
    for i, c in enumerate(cumleler, start=1):
        heceler = " ".join(f"{k}({h})" for k, h in c["kelimeler"])
        satirlar.append(f"\n{i}) {c['metin']}\n   hece: {heceler}")
    if not cumleler:
        satirlar.append(f"\nMetin: {rapor['metin'][:300]}")
    return "\n".join(satirlar)


# --- 2. PDF kelimeleri ile temizlenmiş metnin kelimelerini eşleştirme ---

_TIRELER = "-\u2010\u00ad"


def kelimeleri_eslestir(ham: list[str], tokenler: list[str]) -> list[list[int]] | None:
    """Temizlenmiş metindeki her kelimenin, PDF'teki hangi ham kelime(ler)den geldiğini bulur.

    Satır sonunda bölünmüş kelime PDF'te iki parçadır ("öğren-", "ciler") ama temiz
    metinde tektir ("öğrenciler"). Eşleşme bulunamazsa None döner (o blokta cümle
    vurgusu atlanır, gerisi çizilir).
    """
    sonuc, i = [], 0
    for token in tokenler:
        parcalar = []
        while i < len(ham):
            parcalar.append(i)
            i += 1
            birlesik = "".join(ham[j] for j in parcalar).replace("\u00ad", "")
            tiresiz = "".join(ham[j].rstrip(_TIRELER) if j != parcalar[-1] else ham[j]
                              for j in parcalar).replace("\u00ad", "")
            if token in (birlesik, tiresiz):
                break
            if len(tiresiz) >= len(token):
                return None
        else:
            return None
        sonuc.append(parcalar)
    return sonuc


def _ham_kelimeler(sayfa_kelimeleri: list, bbox) -> list[tuple[pymupdf.Rect, str]]:
    """Bloğun içine düşen PDF kelimeleri, PDF'teki metin sırasıyla."""
    alan = pymupdf.Rect(bbox)
    kelimeler = []
    for x0, y0, x1, y1, kelime, b, l, w in sayfa_kelimeleri:
        r = pymupdf.Rect(x0, y0, x1, y1)
        if alan.contains(pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)):
            # PDF kelimesi içinde görünmez boşluk varsa (ör. \xa0) parçalara ayrılır
            for parca in unicodedata.normalize("NFC", kelime).split():
                kelimeler.append(((b, l, w), r, parca))
    kelimeler.sort(key=lambda k: k[0])
    return [(r, k) for _, r, k in kelimeler]


def cumle_dikdortgenleri(sayfa_kelimeleri: list, blok: Blok) -> list[list[pymupdf.Rect]] | None:
    """Her cümle için vurgulanacak kelime dikdörtgenleri.

    sayfa_kelimeleri: sayfa.get_text("words") çıktısı (sayfa başına bir kez okunur).
    """
    ham = _ham_kelimeler(sayfa_kelimeleri, blok.bbox)
    tokenler = blok.metin.split()
    eslesme = kelimeleri_eslestir([k for _, k in ham], tokenler)
    if eslesme is None:
        return None
    sonuc, t = [], 0
    for cumle in okunabilirlik.cumlelere_bol(blok.metin):
        cumle_tokenleri = cumle.split()
        # cumlelere_bol harf içermeyen parçaları atar; onları atlayarak hizala
        while t < len(tokenler) and tokenler[t:t + len(cumle_tokenleri)] != cumle_tokenleri:
            t += 1
        if t >= len(tokenler):
            return None
        sonuc.append([ham[j][0] for k in range(t, t + len(cumle_tokenleri)) for j in eslesme[k]])
        t += len(cumle_tokenleri)
    return sonuc


# --- 3. Çizim ---

def _yazi_yaz(sekil, nokta, metin, boyut, renk):
    if ACIKLAMA_FONTU.exists():
        sekil.insert_text(nokta, metin, fontsize=boyut, color=renk,
                          fontname="arial", fontfile=str(ACIKLAMA_FONTU))
    else:  # Türkçe karakter desteklemeyen yedek font
        sekil.insert_text(nokta, metin, fontsize=boyut, color=renk)


def sayfayi_isaretle(sayfa: pymupdf.Page, bloklar: list[Blok], tespitler: dict) -> None:
    # Tüm çizim ve yazılar tek bir "şekil" (Shape) içinde toplanıp sayfaya bir kerede
    # yazılır. Her birini ayrı yazmak, sayfanın içerik akışını her seferinde yeniden
    # işlediği için harita sayfalarında (1.500 blok) dakikalar sürüyordu.
    sekil = sayfa.new_shape()

    # Cümle vurguları (yazının üstüne yarı saydam)
    sayfa_kelimeleri = sayfa.get_text("words", flags=_OKUMA_AYARLARI)
    for b in bloklar:
        if b.tur != "paragraf":
            continue
        for i, dikdortgenler in enumerate(cumle_dikdortgenleri(sayfa_kelimeleri, b) or []):
            for r in dikdortgenler:
                sekil.draw_rect(r)
            sekil.finish(color=None, fill=CUMLE_RENKLERI[i % 2], fill_opacity=0.35)

    # Blok çerçeveleri: üzerine gelince açılan notla birlikte
    for b in bloklar:
        r = pymupdf.Rect(b.bbox) + (-1.5, -1.5, 1.5, 1.5)
        not_ = sayfa.add_rect_annot(r)
        not_.set_colors(stroke=RENKLER[b.tur])
        not_.set_border(width=0.8)
        not_.set_info(title=f"Blok {b.blok_no} ({b.tur})", content=rapor_metni(blok_raporu(b)))
        not_.update()
        # "b12" yalnızca ASCII: PDF'in yerleşik fontu yeterli
        sekil.insert_text((r.x0, r.y0 - 0.8), f"b{b.blok_no}", fontsize=5, color=RENKLER[b.tur])

    # Okunabilirlik tespitleri
    for b in bloklar:
        t: Tespit | None = tespitler.get((b.sayfa_no, b.blok_no))
        if t is None:
            continue
        r = pymupdf.Rect(b.bbox) + (-4, -4, 4, 4)
        not_ = sayfa.add_rect_annot(r)
        not_.set_colors(stroke=TESPIT_RENGI)
        not_.set_border(width=2.5)
        not_.set_info(title=f"Okunabilirlik tespiti (güven {t.guven_skoru})",
                      content=f"{t.aciklama}\n\nEn uzun cümle: {t.metin_parcasi}")
        not_.update()

    # Sayfa başlığı ve renk açıklaması
    turler = Counter(b.tur for b in bloklar)
    basili = bloklar[0].basili_sayfa_no if bloklar else None
    _yazi_yaz(sekil, (8, 9),
              f"PDF s.{sayfa.number + 1} / kitap s.{basili or '-'}  |  "
              + "  ".join(f"{t}: {turler[t]}" for t in RENKLER), 7, (0.2, 0.2, 0.2))
    _yazi_yaz(sekil, (8, 17),
              "Çerçeve: yeşil=paragraf  mavi=kısa  kırmızı=bozuk  gri=simge  |  "
              "sarı/turkuaz=cümleler  |  turuncu=okunabilirlik tespiti  |  "
              "ayrıntı için çerçevenin üzerine gelin", 6, (0.2, 0.2, 0.2))
    sekil.commit(overlay=True)


def sayfa_araligi_coz(metin: str, sayfa_sayisi: int) -> list[int]:
    """"28-35,89" -> [28, ..., 35, 89] (1'den başlayan PDF sayfa numaraları)."""
    sayfalar = []
    for parca in metin.split(","):
        eslesme = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", parca)
        if not eslesme:
            raise ValueError(f"Geçersiz sayfa aralığı: {parca!r}")
        bas, son = int(eslesme.group(1)), int(eslesme.group(2) or eslesme.group(1))
        sayfalar += range(bas, son + 1)
    gecersiz = [s for s in sayfalar if not 1 <= s <= sayfa_sayisi]
    if gecersiz:
        raise ValueError(f"PDF'te olmayan sayfa(lar): {gecersiz} (sayfa sayısı {sayfa_sayisi})")
    return sorted(set(sayfalar))


def isaretli_pdf_olustur(pdf_yolu, cikti_yolu, sayfalar: list[int] | None = None,
                         hedef_sinif: int | None = None) -> None:
    # Okunabilirlik kitabın tamamına göre hesaplanır ("en zor %10" kitap geneline göre)
    bloklar = bloklari_cikar(pdf_yolu)
    try:
        _, tespit_listesi = okunabilirlik.analiz_et(bloklar, hedef_sinif)
    except ValueError:  # skorlanabilen paragraf yok: yine de bloklar çizilsin
        tespit_listesi = []
    tespitler = {(t.sayfa_no, t.blok_no): t for t in tespit_listesi}

    with pymupdf.open(pdf_yolu) as belge:
        secili = sayfalar or list(range(1, len(belge) + 1))
        for no in secili:
            sayfa_bloklari = [b for b in bloklar if b.sayfa_no == no]
            sayfayi_isaretle(belge[no - 1], sayfa_bloklari, tespitler)
        belge.select([no - 1 for no in secili])
        belge.save(cikti_yolu, garbage=3, deflate=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Sistemin gözünden PDF")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--sayfalar", help='Ör. "28-35,89" (verilmezse tüm kitap)')
    ap.add_argument("--sinif", type=int, help="Hedef sınıf (verilmezse kapaktan bulunur)")
    arg = ap.parse_args()

    with pymupdf.open(arg.pdf) as belge:
        sayfa_sayisi = len(belge)
    sayfalar = sayfa_araligi_coz(arg.sayfalar, sayfa_sayisi) if arg.sayfalar else None
    cikti = arg.pdf.with_name(arg.pdf.stem + "_isaretli.pdf")
    isaretli_pdf_olustur(arg.pdf, cikti, sayfalar, arg.sinif)
    print(f"{len(sayfalar) if sayfalar else sayfa_sayisi} sayfa işaretlendi -> {cikti}")


if __name__ == "__main__":
    main()
