"""Sunum başlatıcısı: PDF seç -> tüm adımları çalıştır -> inceleme sayfasını tarayıcıda aç.

DEMO.bat'a çift tıklanarak (ya da PDF DEMO.bat'ın üzerine sürüklenerek) çalıştırılır.
Çıktılar veri/demo/<kitap adı>/ klasörüne yazılır; seçilen PDF'e dokunulmaz.

Kullanım:
    python -m derskitabi.demo [kitap.pdf]
"""

import sys
import time
import webbrowser
from collections import Counter
from pathlib import Path

import pymupdf

from .gorsellestir import sayfa_araligi_coz
from .inceleyici import inceleme_html_olustur
from .kayit import bloklari_kaydet, json_kaydet, tespitleri_kaydet
from .kriterler import okunabilirlik, yazim
from .model import BLOK_TURLERI
from .pdf_cikarma import MetinYokHatasi, bloklari_cikar

PROJE_KOKU = Path(__file__).resolve().parent.parent
SANIYE_PER_SAYFA = 0.25  # inceleme sayfası hazırlama süresi tahmini (6. sınıf kitabında ölçüldü)


def pdf_sec() -> Path | None:
    """Komut satırında verilmediyse dosya seçme penceresi açar."""
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        yol = input("PDF dosyasının yolunu yazın: ").strip().strip('"')
        return Path(yol) if yol else None
    kok = tkinter.Tk()
    kok.withdraw()
    kok.attributes("-topmost", True)  # pencere diğer pencerelerin arkasında kalmasın
    yol = filedialog.askopenfilename(
        title="İncelenecek ders kitabı PDF'ini seçin",
        initialdir=str(PROJE_KOKU / "veri"),
        filetypes=[("PDF dosyaları", "*.pdf")],
    )
    kok.destroy()
    return Path(yol) if yol else None


def sayfa_sor(sayfa_sayisi: int) -> list[int] | None:
    tahmin = sayfa_sayisi * SANIYE_PER_SAYFA
    print(f"\nKitapta {sayfa_sayisi} sayfa var. Tamamı için inceleme sayfası yaklaşık "
          f"{tahmin:.0f} saniyede hazırlanır.")
    while True:
        cevap = input("Hangi sayfalar gösterilsin? (Enter = tümü, ör. 13-32 veya 15,30-35): ").strip()
        if not cevap:
            return None
        try:
            return sayfa_araligi_coz(cevap, sayfa_sayisi)
        except ValueError as hata:
            print(f"  {hata}. Tekrar deneyin.")


def adim(no: int, metin: str) -> float:
    print(f"\n[{no}/4] {metin}...")
    return time.perf_counter()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 64)
    print(" Ders Kitaplarında İçerik ve Tutarlılık Hatalarının Tespiti")
    print("=" * 64)

    pdf = pdf_sec()
    if pdf is None:
        print("PDF seçilmedi, çıkılıyor.")
        return
    if not pdf.exists():
        print(f"Dosya bulunamadı: {pdf}")
        return
    print(f"Seçilen kitap: {pdf.name}")

    with pymupdf.open(pdf) as belge:
        sayfa_sayisi = len(belge)
    sayfalar = sayfa_sor(sayfa_sayisi)

    klasor = PROJE_KOKU / "veri" / "demo" / pdf.stem
    klasor.mkdir(parents=True, exist_ok=True)

    # 1. PDF çıkarma
    t = adim(1, "PDF'ten metin blokları çıkarılıyor")
    try:
        bloklar = bloklari_cikar(pdf)
    except MetinYokHatasi as hata:
        print(f"  {hata}")
        return
    bloklari_kaydet(bloklar, klasor / "bloklar.json")
    turler = Counter(b.tur for b in bloklar)
    basili = len({b.sayfa_no for b in bloklar if b.basili_sayfa_no})
    print(f"  {len(bloklar)} blok, {len({b.sayfa_no for b in bloklar})} sayfadan "
          f"({time.perf_counter() - t:.1f} sn)")
    print("  Türler: " + ", ".join(f"{tur} {turler[tur]}" for tur in BLOK_TURLERI))
    print(f"  Basılı sayfa numarası bulunan sayfa: {basili}")

    # 2. Okunabilirlik
    t = adim(2, "Okunabilirlik hesaplanıyor (Ateşman, Çetinkaya-Uzun, Bezirci-Yılmaz)")
    try:
        ozet, tespitler = okunabilirlik.analiz_et(bloklar)
        json_kaydet(ozet.sozluge(), klasor / "okunabilirlik_ozet.json")
        tespitleri_kaydet(tespitler, klasor / "okunabilirlik_tespitler.json")
        hedef = f"{ozet.hedef_sinif}. sınıf" if ozet.hedef_sinif else "kapakta bulunamadı"
        print(f"  Hedef sınıf: {hedef}")
        print(f"  Ateşman {ozet.atesman} ({ozet.atesman_duzeyi}) · "
              f"Çetinkaya-Uzun {ozet.cetinkaya_uzun} ({ozet.cetinkaya_uzun_duzeyi}) · "
              f"Bezirci-Yılmaz {ozet.bezirci_yilmaz} ({ozet.bezirci_yilmaz_duzeyi})")
        print(f"  {ozet.degerlendirilen_paragraf} aday paragraftan {len(tespitler)} tanesi "
              f"işaretlendi ({time.perf_counter() - t:.1f} sn)")
        analiz = (ozet, tespitler)
    except ValueError:
        print("  Skorlanabilen paragraf yok; okunabilirlik atlandı.")
        analiz = (None, [])

    # 3. Yazım (sayfa aralığı seçildiyse yalnız o sayfalar)
    t = adim(3, "Yazım denetleniyor (Starlang + Zemberek, TDK kuralları)")
    secili = set(sayfalar) if sayfalar else None
    atlananlar = Counter()
    yazim_tespitleri = yazim.analiz_et(
        [b for b in bloklar if secili is None or b.sayfa_no in secili], atlananlar=atlananlar,
        kitap_bloklari=bloklar)
    tespitleri_kaydet(yazim_tespitleri, klasor / "yazim_tespitler.json")
    yuksek = sum(t_.guven_skoru == 1.0 for t_ in yazim_tespitleri)
    print(f"  {len(yazim_tespitleri)} yazım tespiti (yüksek güven {yuksek}, "
          f"düşük güven {len(yazim_tespitleri) - yuksek}) ({time.perf_counter() - t:.1f} sn)")
    for tur, n in Counter(t_.alt_tur for t_ in yazim_tespitleri).most_common():
        print(f"    {tur}: {n}")
    print(f"  Sahte hata önlemiyle denetim dışı bırakılan kelime: {sum(atlananlar.values())} "
          f"(özel isim, kısaltma, bölünmüş parça…)")

    # 4. İnceleme sayfası
    t = adim(4, "İnceleme sayfası hazırlanıyor")
    html = klasor / "inceleme.html"
    inceleme_html_olustur(pdf, html, sayfalar, bloklar=bloklar, analiz=analiz,
                          yazim_tespitleri=yazim_tespitleri)
    print(f"  {html} ({html.stat().st_size / 1e6:.1f} MB, {time.perf_counter() - t:.1f} sn)")

    print("\nTarayıcıda açılıyor. Bir kutuya tıklayın: ayrıntılar sağda görünür.")
    webbrowser.open(html.as_uri())


if __name__ == "__main__":
    main()
