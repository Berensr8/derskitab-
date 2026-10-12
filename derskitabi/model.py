"""Projenin ortak veri yapıları.

Tüm modüller bu iki yapıyla konuşur:
  - PDF çıkarma modülü  -> Blok listesi üretir
  - Her kriter modülü   -> Blok listesi alır, Tespit listesi döndürür
"""

from dataclasses import asdict, dataclass, field

# (x0, y0, x1, y1): PDF birimi (point), sayfanın sol üst köşesi orijin.
BBox = tuple[float, float, float, float]

KRITERLER = ("yazim", "okunabilirlik", "tutarlilik")


@dataclass
class Blok:
    """PDF'ten çıkarılan bir metin bloğu. Faz 1'de blok = paragraf kabul edilir."""

    sayfa_no: int  # PDF sayfa indeksi, 1'den başlar (K6)
    blok_no: int  # Sayfa içindeki sıra, 1'den başlar
    bbox: BBox
    metin: str
    # Kitabın üzerinde basılı numara (ör. "15", "iv"); bulunamazsa None (K6)
    basili_sayfa_no: str | None = None

    def sozluge(self) -> dict:
        return asdict(self)

    @classmethod
    def sozlukten(cls, d: dict) -> "Blok":
        d = dict(d)
        d["bbox"] = tuple(d["bbox"])
        return cls(**d)


@dataclass
class Tespit:
    """Bir kriterin bulduğu olası hata."""

    sayfa_no: int  # PDF sayfa indeksi, 1'den başlar (K6)
    blok_no: int
    bbox: BBox
    kriter: str  # KRITERLER içinden biri
    aciklama: str
    guven_skoru: float  # 0.0 (çok emin değil) – 1.0 (kesin)

    # İsteğe bağlı alanlar
    basili_sayfa_no: str | None = None  # Arayüzde "PDF s. 19 / Kitap s. 15" göstermek için
    alt_tur: str | None = None  # Ör. "de_da_ayri_yazim"
    metin_parcasi: str | None = None  # Hatalı kelime/ifade (ileride PDF'te işaretlemek için)
    # Çelişkinin diğer tarafı gibi ilgili başka yerler: [(sayfa_no, blok_no), ...]
    ilgili_konumlar: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self):
        if self.kriter not in KRITERLER:
            raise ValueError(f"Bilinmeyen kriter: {self.kriter!r} (geçerli: {KRITERLER})")
        if not 0.0 <= self.guven_skoru <= 1.0:
            raise ValueError(f"guven_skoru 0 ile 1 arasında olmalı, gelen: {self.guven_skoru}")

    def sozluge(self) -> dict:
        return asdict(self)

    @classmethod
    def sozlukten(cls, d: dict) -> "Tespit":
        d = dict(d)
        d["bbox"] = tuple(d["bbox"])
        d["ilgili_konumlar"] = [tuple(k) for k in d.get("ilgili_konumlar", [])]
        return cls(**d)
