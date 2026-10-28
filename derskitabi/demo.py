"""Sunum başlatıcısı: PDF seç -> tüm adımları çalıştır -> inceleme sayfasını tarayıcıda aç;
ayrıca tespitler kitabın PDF'ine yorum notu olarak işlenir (notlu PDF, K26) ve editörün
karar vereceği Excel raporu yazılır (K27).

DEMO.bat'a çift tıklanarak (ya da PDF DEMO.bat'ın üzerine sürüklenerek) çalıştırılır.
Çıktılar veri/demo/<kitap adı>/ klasörüne yazılır; seçilen PDF'e dokunulmaz.

Kullanım:
    python -m derskitabi.demo [kitap.pdf]
"""

import json
import sys
import time
import webbrowser
from collections import Counter
from pathlib import Path

import pymupdf

from . import yerel_model
from .gorsellestir import sayfa_araligi_coz
from .inceleyici import inceleme_html_olustur
from .kayit import bloklari_kaydet, json_kaydet, tespitleri_kaydet, tespitleri_yukle
from .kriterler import dusuk_oncelik, mufredat, okunabilirlik, tutarlilik, yazim, yazim_hakem
from .model import BLOK_TURLERI
from .pdf_notlari import KRITER_ADLARI, notlu_pdf_olustur
from .rapor import rapor_olustur
from .sonuclar import KitapSonuclari
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
    print(f"\n[{no}/7] {metin}...")
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
    modeller = yerel_model.yuklu_modeller()
    if modeller is None:
        return "Ollama çalışmıyor (OLLAMA_BASLAT.bat ile başlatılabilir)"
    eksik = [m for m in (tutarlilik.GOMME_MODELI, tutarlilik.HAKEM_MODELI, tutarlilik.IKINCI_GORUS_MODELI)
             if m not in modeller and m + ":latest" not in modeller]
    return f"eksik model: {', '.join(eksik)}" if eksik else None


def tutarlilik_adimi(pdf: Path, bloklar, sayfalar, klasor: Path) -> tuple[list | None, list | None]:
    """Önceden hesaplanmış tam kitap sonucu varsa onu kullanır; yoksa (Ollama hazırsa ve
    kullanıcı isterse) seçili sayfalarda çalıştırır; ikisi de olmazsa atlar.
    Döner: (aday kaydı, tespitler) — atlandıysa (None, None)."""
    hazir = pdf.with_name(pdf.stem + "_tutarlilik_adaylar.json")
    hazir_tespitler = pdf.with_name(pdf.stem + "_tutarlilik_tespitler.json")
    if hazir.exists() and hazir_tespitler.exists():
        kayit = json.loads(hazir.read_text(encoding="utf-8"))
        tespit = sum(1 for k in kayit if k.get("guven"))
        print(f"  Önceden hesaplanmış tam kitap sonucu kullanılıyor ({hazir.name}): "
              f"{len(kayit)} cümle çifti karşılaştırılmış, {tespit} bilgi tutarsızlığı tespiti.")
        return kayit, tespitleri_yukle(hazir_tespitler)
    sebep = ollama_hazir_mi()
    if sebep:
        print(f"  Atlandı: {sebep}. İnceleme sayfasında Tutarlılık sekmesi görünmeyecek.")
        return None, None
    kapsam = f"seçili {len(sayfalar)} sayfada" if sayfalar else "kitabın tamamında (uzun sürebilir: 15-45 dk)"
    if not evet_mi(f"  Tutarlılık yerel modellerle {kapsam} çalıştırılsın mı? Bilgisayar şarja takılı olmalı"):
        print("  Atlandı.")
        return None, None
    secili = set(sayfalar) if sayfalar else None
    onbellek_yolu = klasor / "tutarlilik_onbellek.json"
    onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
    kayit = []
    try:
        tespitler = tutarlilik.analiz_et([b for b in bloklar if secili is None or b.sayfa_no in secili],
                                         kayit=kayit, onbellek=onbellek,
                                         ilerleme=lambda m: print(" ", m, flush=True),
                                         haric=tutarlilik.alinti_haric(bloklar, pdf))  # alıntılar (K29)
    finally:
        json_kaydet(onbellek, onbellek_yolu)
    tespitleri_kaydet(tespitler, klasor / "tutarlilik_tespitler.json")
    json_kaydet(kayit, klasor / "tutarlilik_adaylar.json")
    return kayit, tespitler


def mufredat_adimi(bloklar, hedef_sinif: int | None, klasor: Path) -> list | None:
    """Kitabın programı veri/programlar'dan, sınıfı kapaktan bulunur; bulunamazsa adım atlanır (None)."""
    bulunan = mufredat.program_bul(bloklar, hedef_sinif)
    if bulunan is None:
        print("  Kitaba uyan öğretim programı bulunamadı (veri/programlar; sınıf kapaktan okunur). Adım atlandı.")
        return None
    yol, sinif, ciktilar = bulunan
    tespitler = mufredat.kavram_kontrolu(bloklar, ciktilar)
    tespitleri_kaydet(tespitler, klasor / "mufredat_tespitler.json")
    kavram = len({k for c in ciktilar for k in c.kavramlar})
    print(f"  Program: {yol.stem.replace('_programi', '').title()} {sinif}. sınıf — {len(ciktilar)} öğrenme çıktısı, "
          f"{kavram} anahtar kavram")
    for t_ in tespitler:
        print(f"  - {t_.aciklama}")
    if not tespitler:
        print("  Bütün anahtar kavramlar kitabın konu anlatımında geçiyor.")
    return tespitler


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
    # kitap ipuçları: PDF okuma parçası, terim (K29), alıntı (K28)
    yazim_tespitleri = dusuk_oncelik.isaretle(pdf, bloklar, yazim_tespitleri)
    ipucu = Counter(filter(None, map(dusuk_oncelik.sebep, yazim_tespitleri)))
    if ipucu:
        print("  Düşük önceliğe inen kelime tespitleri (silinmez): " +
              ", ".join(f"{ad} {n}" for ad, n in ipucu.most_common()))
    if (yazim_tespitleri and not ollama_hazir_mi()
            and evet_mi("  Kelime tespitleri dil modeline (gemma4) danışılsın mı? Terim ve alıntılar düşük önceliğe iner")):
        onbellek_yolu = PROJE_KOKU / "veri" / "yazim_hakem_onbellek.json"
        onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
        try:
            yazim_tespitleri = yazim_hakem.hakemle(yazim_tespitleri, bloklar, onbellek=onbellek,
                                                   ilerleme=lambda m: print(" ", m, flush=True))
        finally:
            json_kaydet(onbellek, onbellek_yolu)
    tespitleri_kaydet(yazim_tespitleri, klasor / "yazim_tespitler.json")
    yuksek = sum(t_.guven_skoru >= 0.75 for t_ in yazim_tespitleri)
    dusuk_sayisi = sum(t_.guven_skoru < 0.5 for t_ in yazim_tespitleri)
    print(f"  {len(yazim_tespitleri)} yazım tespiti (yüksek güven {yuksek}, düşük öncelik {dusuk_sayisi}) "
          f"({time.perf_counter() - t:.1f} sn)")
    for tur, n in Counter(t_.alt_tur for t_ in yazim_tespitleri).most_common():
        print(f"    {tur}: {n}")
    print(f"  Sahte hata önlemiyle denetim dışı bırakılan kelime: {sum(atlananlar.values())} "
          f"(özel isim, kısaltma, bölünmüş parça…)")

    # 4. Bilgi tutarsızlığı (yerel modeller; hazır sonuç yoksa isteğe bağlı)
    t = adim(4, "Bilgi tutarsızlığı (bge-m3 + gemma4 + Turkish-Gemma)")
    tutarlilik_kaydi, tutarlilik_tespitleri = tutarlilik_adimi(pdf, bloklar, sayfalar, klasor)
    print(f"  ({time.perf_counter() - t:.1f} sn)")

    # 5. İnceleme sayfası
    # 5. Müfredat: programın anahtar kavramları (kural tabanlı, K31 eki)
    t = adim(5, "Müfredat: öğretim programının anahtar kavramları")
    mufredat_tespitleri = mufredat_adimi(bloklar, analiz[0].hedef_sinif if analiz[0] else None, klasor)
    print(f"  ({time.perf_counter() - t:.1f} sn)")

    t = adim(6, "İnceleme sayfası hazırlanıyor")
    html = klasor / "inceleme.html"
    inceleme_html_olustur(pdf, html, sayfalar, bloklar=bloklar, analiz=analiz,
                          yazim_tespitleri=yazim_tespitleri, tutarlilik_kaydi=tutarlilik_kaydi)
    print(f"  {html} ({html.stat().st_size / 1e6:.1f} MB, {time.perf_counter() - t:.1f} sn)")

    # 7. Notlu PDF + Excel raporu (sayfa seçildiyse yalnız o sayfaların tespitleri; kitabın sayfa düzeni değişmez)
    t = adim(7, "Notlu PDF ve Excel raporu hazırlanıyor")
    sec = (lambda liste: [x for x in liste if x.sayfa_no in secili]) if secili else (lambda liste: liste)
    sonuclar = KitapSonuclari(bloklar, {
        "yazim": sec(yazim_tespitleri), "okunabilirlik": sec(analiz[1]),
        "tutarlilik": sec(tutarlilik_tespitleri) if tutarlilik_tespitleri is not None else None,
        "mufredat": mufredat_tespitleri},  # kitabın bütünü için: sayfa seçimine bağlı değil
        analiz[0], tutarlilik_kaydi)
    kapsam = f"Yalnız seçili {len(sayfalar)} sayfa incelendi." if sayfalar else None
    notlu = klasor / f"{pdf.stem}_notlu.pdf"
    sonuc = notlu_pdf_olustur(
        pdf, notlu, bloklar=bloklar, yazim_tespitleri=sonuclar.tespitler["yazim"],
        okunabilirlik_tespitleri=sonuclar.tespitler["okunabilirlik"],
        tutarlilik_tespitleri=sonuclar.tespitler["tutarlilik"], tutarlilik_kaydi=tutarlilik_kaydi, kapsam=kapsam,
        mufredat_tespitleri=mufredat_tespitleri)
    print("  Notlu PDF: " + " · ".join(f"{ad}: {sonuc[k]}" for k, ad in KRITER_ADLARI.items()))
    if sonuc["dusuk_atlanan"]:
        print(f"  Düşük öncelikli {sonuc['dusuk_atlanan']} yazım tespiti PDF'e eklenmedi (raporda var).")
    print(f"  {notlu}")
    print("  Herhangi bir PDF okuyucuda açın: notlar Yorumlar panelinde, liste Yer İmleri panelinde.")
    excel = klasor / f"{pdf.stem}_rapor.xlsx"
    rapor_olustur(excel, sonuclar, pdf.name, sayfa_sayisi, kapsam)
    print(f"  Excel raporu: {excel}")
    print("  Editör sarı 'Editör kararı' sütununu doldurur; özet sayfası isabet oranını kendisi hesaplar.")
    print(f"  ({time.perf_counter() - t:.1f} sn)")

    print("\nTarayıcıda açılıyor. Bir kutuya tıklayın: ayrıntılar sağda görünür.")
    webbrowser.open(html.as_uri())


if __name__ == "__main__":
    main()
