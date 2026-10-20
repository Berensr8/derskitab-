"""Sunum başlatıcısı: PDF seç -> tüm adımları çalıştır -> inceleme sayfasını tarayıcıda aç.

DEMO.bat'a çift tıklanarak (ya da PDF DEMO.bat'ın üzerine sürüklenerek) çalıştırılır.
Çıktılar veri/demo/<kitap adı>/ klasörüne yazılır; seçilen PDF'e dokunulmaz.

Kullanım:
    python -m derskitabi.demo [kitap.pdf]
"""

import json
import sys
import time
import urllib.request
import webbrowser
from collections import Counter
from pathlib import Path

import pymupdf

from .gorsellestir import sayfa_araligi_coz
from .inceleyici import inceleme_html_olustur
from .kayit import bloklari_kaydet, json_kaydet, tespitleri_kaydet
from .kriterler import okunabilirlik, tutarlilik, yazim
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
    print(f"\n[{no}/5] {metin}...")
    return time.perf_counter()


def evet_mi(soru: str, varsayilan: bool = True) -> bool:
    """Yalnız e/evet/h/hayır (ya da Enter = varsayılan) kabul edilir; yanlış tuş tekrar sorulur."""
    while True:
        try:
            cevap = input(f"{soru} ({'E/h' if varsayilan else 'e/H'}): ").strip().lstrip("﻿").lower()
        except EOFError:  # girdi yok (ör. otomatik çalıştırma): varsayılan
            return varsayilan
        if not cevap:
            return varsayilan
        if cevap in ("e", "evet"):
            return True
        if cevap in ("h", "hayır", "hayir"):
            return False
        print("  Lütfen 'e' ya da 'h' yazın (Enter = varsayılan).")


def ollama_hazir_mi() -> str | None:
    """Ollama çalışıyor ve gereken modeller yüklü mü? Değilse sebebi döner."""
    try:
        with urllib.request.urlopen(tutarlilik.OLLAMA_URL + "/api/tags", timeout=3) as cevap:
            modeller = {m["name"] for m in json.loads(cevap.read())["models"]}
    except OSError:
        return "Ollama çalışmıyor (OLLAMA_BASLAT.bat ile başlatılabilir)"
    eksik = [m for m in (tutarlilik.GOMME_MODELI, tutarlilik.HAKEM_MODELI, tutarlilik.IKINCI_GORUS_MODELI)
             if m not in modeller and m + ":latest" not in modeller]
    return f"eksik model: {', '.join(eksik)}" if eksik else None


def tutarlilik_adimi(pdf: Path, bloklar, sayfalar, klasor: Path) -> list | None:
    """Önceden hesaplanmış tam kitap sonucu varsa onu kullanır; yoksa (Ollama hazırsa ve
    kullanıcı isterse) seçili sayfalarda çalıştırır; ikisi de olmazsa atlar."""
    hazir = pdf.with_name(pdf.stem + "_tutarlilik_adaylar.json")
    if hazir.exists():
        kayit = json.loads(hazir.read_text(encoding="utf-8"))
        tespit = sum(1 for k in kayit if k.get("guven"))
        print(f"  Önceden hesaplanmış tam kitap sonucu kullanılıyor ({hazir.name}): "
              f"{len(kayit)} cümle çifti karşılaştırılmış, {tespit} bilgi tutarsızlığı tespiti.")
        return kayit
    sebep = ollama_hazir_mi()
    if sebep:
        print(f"  Atlandı: {sebep}. İnceleme sayfasında Tutarlılık sekmesi görünmeyecek.")
        return None
    kapsam = f"seçili {len(sayfalar)} sayfada" if sayfalar else "kitabın tamamında (uzun sürebilir: 15-45 dk)"
    if not evet_mi(f"  Tutarlılık yerel modellerle {kapsam} çalıştırılsın mı? Bilgisayar şarja takılı olmalı"):
        print("  Atlandı.")
        return None
    secili = set(sayfalar) if sayfalar else None
    onbellek_yolu = klasor / "tutarlilik_onbellek.json"
    onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
    kayit = []
    try:
        tespitler = tutarlilik.analiz_et([b for b in bloklar if secili is None or b.sayfa_no in secili],
                                         kayit=kayit, onbellek=onbellek,
                                         ilerleme=lambda m: print(" ", m, flush=True))
    finally:
        json_kaydet(onbellek, onbellek_yolu)
    tespitleri_kaydet(tespitler, klasor / "tutarlilik_tespitler.json")
    json_kaydet(kayit, klasor / "tutarlilik_adaylar.json")
    return kayit


def test_modu_var_mi(pdf: Path) -> bool:
    from .degerlendirme import set_yukle, test_modu_kaydi_yolu
    try:
        return (any(o["kitap"] == pdf.stem for o in set_yukle())
                and test_modu_kaydi_yolu(pdf.stem, "gelistirme").exists())
    except (OSError, ValueError):
        return False


def test_modu_goster(pdf: Path, klasor: Path) -> None:
    print("\nTEST MODU: kitaba bilerek eklenmiş çelişkiler (geliştirme seti, K20) ile inceleme hazırlanıyor.")
    print("Eklenen cümleler sayfa görüntüsünde görünmez; Tutarlılık sekmesinde metin olarak gösterilir.")
    t = time.perf_counter()
    html = klasor / "inceleme_test_modu.html"
    inceleme_html_olustur(pdf, html, test_modu="gelistirme")
    print(f"  {html} ({html.stat().st_size / 1e6:.1f} MB, {time.perf_counter() - t:.1f} sn)")
    print("\nTarayıcıda açılıyor. Sol listede mor rozetli sayfalara bakın.")
    webbrowser.open(html.as_uri())


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
    klasor = PROJE_KOKU / "veri" / "demo" / pdf.stem
    klasor.mkdir(parents=True, exist_ok=True)
    if test_modu_var_mi(pdf) and not evet_mi(
            "Normal inceleme mi? (Hayır derseniz: bilerek çelişki eklenmiş TEST MODU gösterilir)"):
        test_modu_goster(pdf, klasor)
        return

    with pymupdf.open(pdf) as belge:
        sayfa_sayisi = len(belge)
    sayfalar = sayfa_sor(sayfa_sayisi)

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

    # 4. Bilgi tutarsızlığı (yerel modeller; hazır sonuç yoksa isteğe bağlı)
    t = adim(4, "Bilgi tutarsızlığı (bge-m3 + gemma4 + Turkish-Gemma)")
    tutarlilik_kaydi = tutarlilik_adimi(pdf, bloklar, sayfalar, klasor)
    print(f"  ({time.perf_counter() - t:.1f} sn)")

    # 5. İnceleme sayfası
    t = adim(5, "İnceleme sayfası hazırlanıyor")
    html = klasor / "inceleme.html"
    inceleme_html_olustur(pdf, html, sayfalar, bloklar=bloklar, analiz=analiz,
                          yazim_tespitleri=yazim_tespitleri, tutarlilik_kaydi=tutarlilik_kaydi)
    print(f"  {html} ({html.stat().st_size / 1e6:.1f} MB, {time.perf_counter() - t:.1f} sn)")

    print("\nTarayıcıda açılıyor. Bir kutuya tıklayın: ayrıntılar sağda görünür.")
    webbrowser.open(html.as_uri())


if __name__ == "__main__":
    main()
