"""Etkileşimli PDF inceleyici: sistemin kitabı nasıl okuduğunu tarayıcıda gösterir.

Girdi : PDF dosyası
Çıktı : <kitap>_inceleme.html (tek dosya; çift tıklayınca tarayıcıda açılır, sunucu gerekmez)
  - Sayfa görüntüsü üzerinde bloklar (renk = tür). Bloğa tıklayınca yan panelde:
    neden bu türde sayıldığı, cümleleri, kelimelerin hece sayıları, formül hesabının
    adımları ve varsa okunabilirlik tespiti.
  - Yan panelde sayfadaki tüm bloklar listelenir (küçük kutulara listeden ulaşılır).

Kullanım:
    python -m derskitabi.inceleyici veri/kitap.pdf [--sayfalar 10-35] [--sinif 6]

Bilgi gorsellestir.blok_raporu() ile üretilir (işaretli PDF ile aynı kaynak, K12).
"""

import argparse
import base64
import json
import sys
from pathlib import Path

import pymupdf

from .gorsellestir import blok_raporu, cumle_dikdortgenleri, sayfa_araligi_coz
from .kriterler import okunabilirlik
from .model import Blok, Tespit
from .pdf_cikarma import _OKUMA_AYARLARI, bloklari_cikar

SABLON = Path(__file__).parent / "sablonlar" / "inceleyici.html"
GORUNTU_DPI = 110


def satirlari_birlestir(dikdortgenler: list[pymupdf.Rect]) -> list[list[float]]:
    """Aynı satırdaki ardışık kelime kutularını tek kutuya birleştirir (daha düzgün vurgu)."""
    satirlar: list[pymupdf.Rect] = []
    for r in dikdortgenler:
        son = satirlar[-1] if satirlar else None
        if son is not None and abs(son.y0 - r.y0) < 2 and abs(son.y1 - r.y1) < 2 and r.x0 >= son.x0:
            satirlar[-1] = son | r
        else:
            satirlar.append(pymupdf.Rect(r))
    return [[round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)] for r in satirlar]


def _tespit_verisi(t: Tespit | None) -> dict | None:
    if t is None:
        return None
    return {"aciklama": t.aciklama, "guven": t.guven_skoru, "metin_parcasi": t.metin_parcasi}


def sayfa_verisi(sayfa: pymupdf.Page, bloklar: list[Blok], tespitler: dict) -> dict:
    goruntu = sayfa.get_pixmap(dpi=GORUNTU_DPI).tobytes("jpeg", jpg_quality=80)
    kelimeler = sayfa.get_text("words", flags=_OKUMA_AYARLARI)
    veri_bloklari = []
    for b in bloklar:
        cumleler = cumle_dikdortgenleri(kelimeler, b) if b.tur == "paragraf" else None
        veri_bloklari.append({
            "bbox": [round(v, 1) for v in b.bbox],
            "rapor": blok_raporu(b),
            "cumle_kutulari": [satirlari_birlestir(c) for c in cumleler] if cumleler else [],
            "tespit": _tespit_verisi(tespitler.get((b.sayfa_no, b.blok_no))),
        })
    return {
        "no": sayfa.number + 1,
        "basili": bloklar[0].basili_sayfa_no if bloklar else None,
        "genislik": round(sayfa.rect.width, 1),
        "yukseklik": round(sayfa.rect.height, 1),
        "goruntu": "data:image/jpeg;base64," + base64.b64encode(goruntu).decode("ascii"),
        "bloklar": veri_bloklari,
    }


def inceleme_html_olustur(pdf_yolu, cikti_yolu, sayfalar: list[int] | None = None,
                          hedef_sinif: int | None = None) -> None:
    bloklar = bloklari_cikar(pdf_yolu)
    try:
        ozet, tespit_listesi = okunabilirlik.analiz_et(bloklar, hedef_sinif)
        ozet_verisi = ozet.sozluge()
    except ValueError:  # skorlanabilen paragraf yok
        ozet_verisi, tespit_listesi = None, []
    tespitler = {(t.sayfa_no, t.blok_no): t for t in tespit_listesi}

    with pymupdf.open(pdf_yolu) as belge:
        secili = sayfalar or list(range(1, len(belge) + 1))
        sayfa_listesi = [
            sayfa_verisi(belge[no - 1], [b for b in bloklar if b.sayfa_no == no], tespitler)
            for no in secili
        ]

    veri = {
        "kitap": Path(pdf_yolu).name,
        "ozet": ozet_verisi,
        "toplam_tespit": len(tespit_listesi),
        "min_cumle": okunabilirlik.MIN_CUMLE,
        "sayfalar": sayfa_listesi,
    }
    # "</" kaçışı: kitap metninde "</script>" geçse bile sayfa bozulmasın
    json_metin = json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")
    html = SABLON.read_text(encoding="utf-8").replace("/*__VERI__*/null", json_metin)
    Path(cikti_yolu).write_text(html, encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Etkileşimli PDF inceleyici")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--sayfalar", help='Ör. "10-35,89" (verilmezse tüm kitap; büyük dosya olur)')
    ap.add_argument("--sinif", type=int, help="Hedef sınıf (verilmezse kapaktan bulunur)")
    arg = ap.parse_args()

    with pymupdf.open(arg.pdf) as belge:
        sayfa_sayisi = len(belge)
    sayfalar = sayfa_araligi_coz(arg.sayfalar, sayfa_sayisi) if arg.sayfalar else None
    cikti = arg.pdf.with_name(arg.pdf.stem + "_inceleme.html")
    inceleme_html_olustur(arg.pdf, cikti, sayfalar, arg.sinif)
    boyut = cikti.stat().st_size / 1e6
    print(f"{len(sayfalar) if sayfalar else sayfa_sayisi} sayfa -> {cikti} ({boyut:.1f} MB)")
    print("Dosyaya çift tıklayarak tarayıcıda açabilirsiniz.")


if __name__ == "__main__":
    main()
