"""PDF'ten metin bloklarını çıkarma (Faz 1, adım 1).

Girdi : PDF dosyası
Çıktı : Blok listesi (sayfa_no, blok_no, bbox, metin, basili_sayfa_no, tur)

Kullanım:
    python -m derskitabi.pdf_cikarma veri/kitap.pdf
"""

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf

from .kayit import bloklari_kaydet
from .model import BLOK_TURLERI, Blok

# Sayfanın üstünden ve altından bu oranda bir şerit "kenar" sayılır. Kenarda tek
# başına duran bir sayı, basılı sayfa numarası kabul edilir.
KENAR_ORANI = 0.08
_SAYFA_NO_DESENI = re.compile(r"^\d{1,4}$")

# PyMuPDF metin okuma ayarı: TEXT_PRESERVE_LIGATURES verilmediği için "ﬁ" gibi
# bitişik harfler normal harflere ("f" + "i") açılır; aksi halde yazım kriteri
# bu kelimeleri hatalı sanar.
_OKUMA_AYARLARI = pymupdf.TEXT_MEDIABOX_CLIP

# Satır sonunda bölünmüş kelimeler ("öğren-" + "ciler"):
#  - Yumuşak tire (U+00AD) yalnızca satır bölmek için vardır, her zaman silinir.
#    Dizgi programları satır sonu tiresini çoğu zaman bu karakterle kodlar;
#    PyMuPDF'in kendi TEXT_DEHYPHENATE ayarı bunu tanımadığı için kendimiz yapıyoruz.
#  - Normal tire (-) yalnızca sonraki satır küçük harfle başlıyorsa silinir;
#    böylece satır sonuna denk gelen "Türk-Yunan", "1923-1938" gibi gerçek
#    tireler korunur (yalnızca aradaki satır sonu kaldırılır).
_YUMUSAK_TIRE = re.compile("­\\s*")
_SATIR_SONU_TIRESI = re.compile(r"(\w)[-‐]\n\s*(?=[a-zçğıöşüâîû])")
_GERCEK_TIRE_SATIR_SONU = re.compile(r"([-‐])\n\s*")

# Bu kadar ve daha fazla kelimeli bloklar "paragraf" sayılır (K8).
PARAGRAF_ESIGI = 5


class MetinYokHatasi(Exception):
    """PDF'te seçilebilir metin yok (taranmış kitap). OCR Faz 1 kapsamı dışında."""


def _metni_temizle(ham: str) -> str:
    # Bazı PDF'ler "Ç" harfini "C" + ayrı çengel işareti olarak saklar; NFC
    # normalleştirmesi bunları tek karaktere birleştirir.
    metin = unicodedata.normalize("NFC", ham)
    metin = _YUMUSAK_TIRE.sub("", metin)
    metin = _SATIR_SONU_TIRESI.sub(r"\1", metin)
    metin = _GERCEK_TIRE_SATIR_SONU.sub(r"\1", metin)
    # Kalan satır sonları ve fazla boşluklar tek boşluğa indirilir.
    return " ".join(metin.split())


def blok_turu(metin: str) -> str:
    """Bloğun hangi kriterlerce analiz edileceğini belirleyen tür (K8)."""
    if "�" in metin:  # Unicode karşılığı olmayan karakter: metin okunamıyor
        return "bozuk"
    if not any(c.isalnum() for c in metin):
        return "simge"
    if len(metin.split()) >= PARAGRAF_ESIGI:
        return "paragraf"
    return "kisa"


def _sayfa_etiketi(sayfa: pymupdf.Page) -> str | None:
    """PDF'te tanımlı sayfa etiketi (basılı numara); yoksa None."""
    try:
        return sayfa.get_label() or None
    except IndexError:
        # PyMuPDF, etiketler sonraki bir sayfadan başlıyorsa (ör. kapak etiketsiz)
        # etiketsiz sayfada hata veriyor; bu sayfanın etiketi yok demektir.
        return None


def _kenarda_mi(bbox, sayfa_yuksekligi: float) -> bool:
    ust_sinir = sayfa_yuksekligi * KENAR_ORANI
    alt_sinir = sayfa_yuksekligi * (1 - KENAR_ORANI)
    return bbox[3] <= ust_sinir or bbox[1] >= alt_sinir


def sayfa_bloklari(sayfa: pymupdf.Page) -> list[Blok]:
    """Tek bir sayfanın metin bloklarını döndürür."""
    sayfa_no = sayfa.number + 1  # PyMuPDF 0'dan sayar, biz 1'den (K6)
    basili_no = _sayfa_etiketi(sayfa)  # 1. yol: PDF'in sayfa etiketi
    yukseklik = sayfa.rect.height

    adaylar = []
    for x0, y0, x1, y1, ham, _, tur in sayfa.get_text("blocks", flags=_OKUMA_AYARLARI):
        metin = _metni_temizle(ham)
        if tur != 0 or not metin:  # 0 = metin bloğu (1 = görsel)
            continue
        bbox = (x0, y0, x1, y1)
        if _kenarda_mi(bbox, yukseklik) and _SAYFA_NO_DESENI.match(metin):
            # Sayfa numarası bloğu: analiz edilecek bir paragraf değil, ayıklanır.
            if basili_no is None:  # 2. yol: kenardaki sayı
                basili_no = metin
            continue
        adaylar.append((bbox, metin))

    # Okuma sırası (K7): PyMuPDF blokları PDF'e yazıldıkları sırayla verir; biz
    # yukarıdan aşağıya, aynı yükseklikte soldan sağa sıralarız (önce y0, sonra x0).
    adaylar.sort(key=lambda a: (a[0][1], a[0][0]))

    return [
        Blok(sayfa_no, i, bbox, metin, basili_no, blok_turu(metin))
        for i, (bbox, metin) in enumerate(adaylar, start=1)
    ]


def bloklari_cikar(pdf_yolu) -> list[Blok]:
    """PDF'in tüm sayfalarındaki metin bloklarını sırayla döndürür."""
    with pymupdf.open(pdf_yolu) as belge:
        bloklar = [b for sayfa in belge for b in sayfa_bloklari(sayfa)]
    if not bloklar:
        raise MetinYokHatasi(
            f"{pdf_yolu}: seçilebilir metin bulunamadı. PDF taranmış görüntülerden "
            "oluşuyor olabilir; OCR Faz 1 kapsamı dışında."
        )
    return bloklar


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("Kullanım: python -m derskitabi.pdf_cikarma <kitap.pdf>")
        sys.exit(1)

    pdf = Path(sys.argv[1])
    bloklar = bloklari_cikar(pdf)
    cikti = pdf.with_name(pdf.stem + "_bloklar.json")
    bloklari_kaydet(bloklar, cikti)

    sayfalar = {b.sayfa_no for b in bloklar}
    basili = {b.sayfa_no for b in bloklar if b.basili_sayfa_no}
    print(f"{len(bloklar)} blok, {len(sayfalar)} sayfadan çıkarıldı -> {cikti}")
    print(f"Basılı sayfa numarası bulunan sayfa: {len(basili)} / {len(sayfalar)}")
    turler = Counter(b.tur for b in bloklar)
    print("Blok türleri: " + ", ".join(f"{t} {turler[t]}" for t in BLOK_TURLERI))
    for b in bloklar[:5]:
        print(f"  [PDF s.{b.sayfa_no} / kitap s.{b.basili_sayfa_no or '-'} / blok {b.blok_no}] "
              f"{b.metin[:80]}")


if __name__ == "__main__":
    main()
