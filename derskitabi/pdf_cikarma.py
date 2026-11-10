"""PDF'ten metin bloklarını çıkarma (Faz 1, adım 1).

Girdi : PDF dosyası
Çıktı : Blok listesi (sayfa_no, blok_no, bbox, metin, basili_sayfa_no, tur)

Kullanım:
    python -m derskitabi.pdf_cikarma veri/kitap.pdf
"""

import difflib
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
# InDesign ActualText etiketindeki hatalı I/İ eşlemelerini (büyük başlıklardaki
# 'İ' yerine 'I' etiketi) düzeltmek için kullanılan alternatif okuma (K41-ek2).
_OKUMA_AYARLARI_NOACT = pymupdf.TEXT_MEDIABOX_CLIP | pymupdf.TEXT_IGNORE_ACTUALTEXT

# Satır sonunda bölünmüş kelimeler ("öğren-" + "ciler"):
#  - Yumuşak tire (U+00AD) satır sonunda heceleme tiresidir, silinir.
#  - Satır ortasında iki karakter arasındaki U+00AD görünür kısa çizgidir (K41-ek2).
#  - Normal tire (-) yalnızca sonraki satır küçük harfle başlıyorsa silinir;
#    ancak kitap içinde tireyle yazılan birleşik kelimeler ("asit-baz") korunur.
#    Büyük harfle devam eden ("Türk-Yunan", "1923-1938") gerçek tireler korunur.
_YUMUSAK_TIRE = re.compile("­\\s*")
_GERCEK_TIRE_SATIR_SONU = re.compile(r"([-‐])\s*\n\s*")

# Bu kadar ve daha fazla kelimeli bloklar "paragraf" sayılır (K8).
PARAGRAF_ESIGI = 5


class MetinYokHatasi(Exception):
    """PDF'te seçilebilir metin yok (taranmış kitap). OCR Faz 1 kapsamı dışında."""


def _kucuk_harf_tr(s: str) -> str:
    """Türkçe I/ı ve İ/i duyarlı küçük harfe çevirme."""
    return s.replace("I", "ı").replace("İ", "i").lower()


def _i_duzelt(ham_norm: str, ham_noact: str) -> str:
    """ActualText etiketi 'I' olan fakat font glifinde gerçekte 'İ' olan harfleri düzeltir."""
    if "I" not in ham_norm or "İ" not in ham_noact:
        return ham_norm
    s = difflib.SequenceMatcher(None, ham_norm, ham_noact)
    parcalar = []
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "equal":
            parcalar.append(ham_norm[i1:i2])
        elif tag == "replace" and ham_norm[i1:i2] == "I" and ham_noact[j1:j2] == "İ":
            parcalar.append("İ")
        else:
            parcalar.append(ham_norm[i1:i2])
    return "".join(parcalar)


def tireli_kelimeleri_topla(belge: pymupdf.Document) -> set[str]:
    """Kitap genelinde tireyle yazılmış kelimeleri (örn. 'asit-baz') toplar."""
    tireli = set()
    for sayfa in belge:
        text = sayfa.get_text(flags=_OKUMA_AYARLARI)
        text = re.sub(r"(\S)\xad(\S)", r"\1-\2", text)
        for m in re.finditer(r"\b([a-zçğıöşüâîû]+(?:-[a-zçğıöşüâîû]+)+)\b", _kucuk_harf_tr(text)):
            tireli.add(m.group(1))
    return tireli


def _metni_temizle(ham: str, tireli_kelimeler: set[str] | None = None) -> str:
    # Bazı PDF'ler "Ç" harfini "C" + ayrı çengel işareti olarak saklar; NFC
    # normalleştirmesi bunları tek karaktere birleştirir.
    metin = unicodedata.normalize("NFC", ham)
    # Kontrol karakterlerini ve öğrenci satırı artıklarını temizle
    metin = re.sub(r"[\x08\ufeff\u200c]", " ", metin)
    # 1. Satır ortasında iki boşluk olmayan karakter arasındaki U+00AD görünür tire '-' olur (K41-ek2)
    metin = re.sub(r"(\S)\xad(\S)", r"\1-\2", metin)

    if tireli_kelimeler is None:
        tireli_kelimeler = set()

    # 2. Satır sonu tiresi: kitapta tireyle geçen kelimeler ("asit-baz") korunur,
    # diğer küçük harfle devam eden hecelemeler birleştirilir ("öğren-" + "ciler" -> "öğrenciler").
    def repl(m):
        sol, sag = m.group(1), m.group(2)
        bilesik = f"{_kucuk_harf_tr(sol)}-{_kucuk_harf_tr(sag)}"
        if bilesik in tireli_kelimeler:
            return f"{sol}-{sag}"
        if sag[0].islower() or sag[0] in "çğıöşüâîû":
            return f"{sol}{sag}"
        return f"{sol}-{sag}"

    metin = re.sub(r"([a-zçğıöşüâîûA-ZÇĞİÖŞÜÂÎÛ0-9]+)[-‐\xad]\s*\n\s*([a-zçğıöşüâîûA-ZÇĞİÖŞÜÂÎÛ0-9]+)", repl, metin)
    metin = _YUMUSAK_TIRE.sub("", metin)
    metin = _GERCEK_TIRE_SATIR_SONU.sub(r"\1", metin)
    # Kalan satır sonları ve fazla boşluklar tek boşluğa indirilir.
    return " ".join(metin.split())


def blok_turu(metin: str) -> str:
    """Bloğun hangi kriterlerce analiz edileceğini belirleyen tür (K8)."""
    if "\ufffd" in metin:  # Unicode karşılığı olmayan karakter: metin okunamıyor
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


def sayfa_bloklari(sayfa: pymupdf.Page, tireli_kelimeler: set[str] | None = None) -> list[Blok]:
    """Tek bir sayfanın metin bloklarını döndürür."""
    sayfa_no = sayfa.number + 1  # PyMuPDF 0'dan sayar, biz 1'den (K6)
    basili_no = _sayfa_etiketi(sayfa)  # 1. yol: PDF'in sayfa etiketi
    yukseklik = sayfa.rect.height

    adaylar = []
    blocks_norm = sayfa.get_text("blocks", flags=_OKUMA_AYARLARI)
    has_I = any("I" in b[4] for b in blocks_norm if b[6] == 0)
    noact_map = {}
    if has_I:
        blocks_noact = sayfa.get_text("blocks", flags=_OKUMA_AYARLARI_NOACT)
        for b in blocks_noact:
            if b[6] == 0:
                kutu = (round(b[0], 1), round(b[1], 1), round(b[2], 1), round(b[3], 1))
                noact_map[kutu] = b[4]

    for x0, y0, x1, y1, ham, _, tur in blocks_norm:
        if tur != 0:  # 0 = metin bloğu (1 = görsel)
            continue
        kutu = (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1))
        if has_I and "I" in ham and kutu in noact_map:
            ham = _i_duzelt(ham, noact_map[kutu])
        metin = _metni_temizle(ham, tireli_kelimeler)
        if not metin:
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
        tireli = tireli_kelimeleri_topla(belge)
        bloklar = [b for sayfa in belge for b in sayfa_bloklari(sayfa, tireli_kelimeler=tireli)]
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


if __name__ == "__main__":
    main()
