"""Excel inceleme raporu (Faz 2, K27): tespitler tablo hâlinde, editörün karar vereceği sütunlarla.

Girdi : PDF dosyası (+ varsa veri klasöründeki çıkarma ve tutarlılık sonuçları)
Çıktı : <kitap>_rapor.xlsx
  - Özet     : kitap bilgisi, kriter başına tespit sayıları (öncelik ve editör kararına göre;
               formüllerle, editör karar girdikçe güncellenir), okunabilirlik kitap puanları,
               sistemin ölçülmüş başarısı, nasıl kullanılır
  - Tespitler: her satır bir tespit (kitaptaki sıraya göre); filtreli, başlık sabit.
               Sarı sütunlar editör için: "Editör kararı" (Hata / Hata değil / Emin değilim) ve not.
Editörün doldurduğu dosya geri okunabilir (--oku): gerçek kitapta isabet oranı ölçülür —
uzman geri bildiriminin ilk adımı.

Kullanım:
    python -m derskitabi.rapor veri/kitap.pdf [--sinif 6] [--hakem]
    python -m derskitabi.rapor --oku veri/kitap_rapor.xlsx
"""

import argparse
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .kriterler import dusuk_oncelik
from .model import Tespit
from .pdf_notlari import KRITER_ADLARI, KURAL_ADLARI, karsi_cumle, konum_metni, oncelik
from .sonuclar import KitapSonuclari, sonuclari_topla

PROJE = Path(__file__).resolve().parent.parent
KARARLAR = ("Hata", "Hata değil", "Emin değilim")
YAZI = "Arial"
SUTUNLAR = [  # (başlık, genişlik)
    ("No", 6), ("Kriter", 18), ("Tür", 20), ("PDF s.", 8), ("Kitap s.", 8), ("İlgili metin", 40),
    ("Açıklama", 60), ("Öneri", 16), ("Karşı cümle (tutarlılık)", 40), ("Güven", 8), ("Öncelik", 10),
    ("Editör kararı", 16), ("Editör notu", 30), ("Kimlik", 10),
]
SUTUN = {ad: i + 1 for i, (ad, _) in enumerate(SUTUNLAR)}  # başlık -> sütun numarası (1'den)
HARF = {ad: chr(ord("A") + i) for i, (ad, _) in enumerate(SUTUNLAR)}
TUR_ADLARI = {"morfoloji": "kelime (yazım)", "kitap_ici_zor_paragraf": "zor paragraf",
              "kitap_ici_celiski": "kitap içi çelişki", **{k: f"TDK kuralı: {v}" for k, v in KURAL_ADLARI.items()}}
ONCELIK_RENGI = {"yüksek": "F8CBAD", "orta": "FFE699", "düşük": "D9D9D9"}
GIRDI_RENGI = "FFF2CC"  # editörün dolduracağı hücreler
BASLIK_RENGI = "1F4E79"
# Sistemin geliştirme sırasında ölçülmüş başarısı (bilerek eklenmiş hatalar ve elle etiketlerle).
# Kaynak: testseti/*_sonuclari.md. Sistem değişirse burası da güncellenmeli.
OLCULEN_BASARI = [
    ("Yazım ve dil", "Bilerek eklenmiş 56 yazım hatasının 55'i bulundu (kilitli test seti, hakemli).",
     "testseti/yazim_sonuclari.md (K23, K25)"),
    ("Yazım ve dil", "Gerçek kitapta isabet düşük: Matematik 11'de gösterilen tespitlerin %27'si gerçek hata "
     "(çoğu terim, özel isim, alıntı). TDK kuralları 9 tespitin 8'inde isabetli.",
     "testseti/yazim_sonuclari.md (K23, K25)"),
    ("Dilsel karmaşıklık (okunabilirlik)", "Formüller sınıf düzeyini ayırt etmiyor (aynı ders içinde de); "
     "cümle ve kelime uzunluğunu ölçüyor. Tespitler 'dilsel karmaşıklık uyarısı' olarak okunmalı.",
     "testseti/okunabilirlik_sonuclari.md (K24)"),
    ("Bilgi tutarsızlığı", "Bilerek eklenmiş 35 çelişkinin 27'si bulundu (%77); bulunanların hepsi gerçekten "
     "çelişkiydi (%100). En zayıf: 'en/ilk' ve sözel çelişkiler.",
     "testseti/tutarlilik_sonuclari.md (K20)"),
]


def _surum() -> str:
    """Sistem sürümü (git commit); kodda commit edilmemiş değişiklik varsa belirtilir."""
    try:
        kisa = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJE, capture_output=True,
                              text=True, check=True).stdout.strip()
        kirli = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=PROJE,
                               capture_output=True, text=True, check=True).stdout.strip()
        return kisa + (" (+ kaydedilmemiş değişiklik)" if kirli else "")
    except (OSError, subprocess.CalledProcessError):
        return "-"


def kimlik(t: Tespit) -> str:
    """Satırı tespite bağlayan anahtar (editör satırları sıralasa da kararlar doğru eşleşsin)."""
    return f"{t.kriter}|{t.sayfa_no}|{t.blok_no}|{t.alt_tur}|{(t.metin_parcasi or '')[:80]}"


def oneri(t: Tespit) -> str:
    m = re.search(r"Önerilen yazım: '([^']+)'", t.aciklama)
    return m.group(1) if m else ""


def tespit_satirlari(sonuclar: KitapSonuclari) -> list[dict]:
    """Bütün tespitler, kitaptaki sıraya göre (sayfa, sayfadaki konum), birer satır."""
    bloklar = {(b.sayfa_no, b.blok_no): b for b in sonuclar.bloklar}
    satirlar = []
    for kriter in KRITER_ADLARI:
        for t in sonuclar.tespitler.get(kriter) or []:
            karsi = ""
            if kriter == "tutarlilik" and t.ilgili_konumlar:
                b = bloklar.get(tuple(t.ilgili_konumlar[0]))
                yer = konum_metni(b.sayfa_no, b.basili_sayfa_no) if b else f"PDF s. {t.ilgili_konumlar[0][0]}"
                karsi = f"{yer}: {karsi_cumle(t, sonuclar.tutarlilik_kaydi) or '(cümle bulunamadı)'}"
            satirlar.append({
                "sira": (t.sayfa_no, t.bbox[1], t.bbox[0]),
                "Kriter": KRITER_ADLARI[kriter],
                "Tür": TUR_ADLARI.get(t.alt_tur, t.alt_tur or "") + (f" — {s}" if (s := dusuk_oncelik.sebep(t)) else ""),
                "PDF s.": t.sayfa_no, "Kitap s.": t.basili_sayfa_no or "", "İlgili metin": t.metin_parcasi or "",
                "Açıklama": t.aciklama, "Öneri": oneri(t), "Karşı cümle (tutarlılık)": karsi,
                "Güven": t.guven_skoru, "Öncelik": oncelik(t.guven_skoru), "Kimlik": kimlik(t),
            })
    satirlar.sort(key=lambda s: s["sira"])
    for i, s in enumerate(satirlar, start=1):
        s["No"] = i
    return satirlar


def _yazi(kalin=False, boyut=10, renk="000000") -> Font:
    return Font(name=YAZI, bold=kalin, size=boyut, color=renk)


def _dolgu(renk: str) -> PatternFill:
    return PatternFill("solid", start_color=renk, end_color=renk)


def _tespitler_sayfasi(ws, satirlar: list[dict]) -> None:
    ws.title = "Tespitler"
    for (ad, genislik), harf in zip(SUTUNLAR, HARF.values()):
        h = ws.cell(row=1, column=SUTUN[ad], value=ad)
        h.font, h.fill = _yazi(kalin=True, renk="FFFFFF"), _dolgu(BASLIK_RENGI)
        h.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[harf].width = genislik
    ws.row_dimensions[1].height = 30
    son = len(satirlar) + 1
    for r, s in enumerate(satirlar, start=2):
        for ad, _ in SUTUNLAR:
            c = ws.cell(row=r, column=SUTUN[ad], value=s.get(ad))
            c.font = _yazi()
            c.alignment = Alignment(wrap_text=ad in ("İlgili metin", "Açıklama", "Karşı cümle (tutarlılık)",
                                                     "Editör notu"), vertical="top")
        ws.cell(row=r, column=SUTUN["Güven"]).number_format = "0.00"
        ws.cell(row=r, column=SUTUN["Öncelik"]).fill = _dolgu(ONCELIK_RENGI[s["Öncelik"]])
        for ad in ("Editör kararı", "Editör notu"):
            ws.cell(row=r, column=SUTUN[ad]).fill = _dolgu(GIRDI_RENGI)
    karar = DataValidation(type="list", formula1='"' + ",".join(KARARLAR) + '"', allow_blank=True,
                           showErrorMessage=True, errorTitle="Geçersiz karar",
                           error="Listeden seçin: " + " / ".join(KARARLAR))
    ws.add_data_validation(karar)
    if satirlar:
        karar.add(f"{HARF['Editör kararı']}2:{HARF['Editör kararı']}{son}")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{HARF['Kimlik']}{max(son, 2)}"
    ws.column_dimensions[HARF["Kimlik"]].hidden = True  # yalnız geri okuma için


def _hucre(ws, r, c, deger, **bicim):
    h = ws.cell(row=r, column=c, value=deger)
    h.font = bicim.pop("yazi", _yazi())
    for k, v in bicim.items():
        setattr(h, k, v)
    return h


def _ozet_sayfasi(ws, sonuclar: KitapSonuclari, kitap: str, sayfa_sayisi: int | None, kapsam: str | None) -> None:
    ws.title = "Özet"
    ws.column_dimensions["A"].width = 36
    for harf in "BCDEFGHIJ":
        ws.column_dimensions[harf].width = 13
    _hucre(ws, 1, 1, "Ders Kitabı İnceleme Raporu", yazi=_yazi(kalin=True, boyut=14))
    ozet = sonuclar.okunabilirlik_ozeti
    bilgiler = [("Kitap", kitap), ("PDF sayfa sayısı", sayfa_sayisi or "-"),
                ("Hedef sınıf", f"{ozet.hedef_sinif}. sınıf" if ozet and ozet.hedef_sinif else "bulunamadı"),
                ("Rapor tarihi", date.today().strftime("%d.%m.%Y")), ("Sistem sürümü", _surum()),
                ("Kapsam", kapsam or "Kitabın tamamı")]
    for i, (ad, deger) in enumerate(bilgiler, start=3):
        _hucre(ws, i, 1, ad, yazi=_yazi(kalin=True))
        _hucre(ws, i, 2, deger)

    # Kriter tablosu: sayılar formülle (editör karar girdikçe güncellenir)
    r0 = len(bilgiler) + 4
    _hucre(ws, r0 - 1, 1, "Tespitler (formüller Tespitler sayfasından sayar)", yazi=_yazi(kalin=True, boyut=12))
    basliklar = ["Kriter", "Tespit", "Yüksek", "Orta", "Düşük", "Hata", "Hata değil", "Emin değilim",
                 "Bakılmadı", "İsabet"]
    for c, ad in enumerate(basliklar, start=1):
        _hucre(ws, r0, c, ad, yazi=_yazi(kalin=True, renk="FFFFFF"), fill=_dolgu(BASLIK_RENGI),
               alignment=Alignment(wrap_text=True, horizontal="center"))
    kr, on, ed = (f"Tespitler!${HARF[a]}:${HARF[a]}" for a in ("Kriter", "Öncelik", "Editör kararı"))
    for i, (kriter, ad) in enumerate(KRITER_ADLARI.items(), start=1):
        r = r0 + i
        _hucre(ws, r, 1, ad)
        if sonuclar.tespitler.get(kriter) is None:
            _hucre(ws, r, 2, "çalıştırılmadı", yazi=_yazi(renk="808080"))
            continue
        _hucre(ws, r, 2, f'=COUNTIFS({kr},$A{r})')
        for c, deger in zip((3, 4, 5), ("yüksek", "orta", "düşük")):
            _hucre(ws, r, c, f'=COUNTIFS({kr},$A{r},{on},"{deger}")')
        for c, deger in zip((6, 7, 8), KARARLAR):
            _hucre(ws, r, c, f'=COUNTIFS({kr},$A{r},{ed},"{deger}")')
        _hucre(ws, r, 9, f"=B{r}-F{r}-G{r}-H{r}")
        _hucre(ws, r, 10, f'=IFERROR(F{r}/(F{r}+G{r}),"-")', number_format="0%")
    r = r0 + len(KRITER_ADLARI) + 1
    _hucre(ws, r, 1, "Toplam", yazi=_yazi(kalin=True))
    for c in range(2, 10):
        harf = "ABCDEFGHIJ"[c - 1]
        _hucre(ws, r, c, f"=SUM({harf}{r0 + 1}:{harf}{r - 1})", yazi=_yazi(kalin=True))
    _hucre(ws, r, 10, f'=IFERROR(F{r}/(F{r}+G{r}),"-")', yazi=_yazi(kalin=True), number_format="0%")
    _hucre(ws, r + 1, 1, "İsabet = Hata / (Hata + Hata değil): editörün baktığı tespitlerin gerçekten hata "
           "olanların oranı. Öncelik: yüksek ≥ 0,75 güven, orta ≥ 0,5, düşük = PDF okuma parçası, kitabın terimi, alıntı metin ya da dil modeli 'muhtemelen doğru' dedi.",
           yazi=_yazi(boyut=9, renk="595959"))

    # Okunabilirlik kitap puanları (sistemin hesabı)
    r += 3
    _hucre(ws, r, 1, "Kitabın genel dilsel karmaşıklığı (paragraf puanlarının ortancası)",
           yazi=_yazi(kalin=True, boyut=12))
    if ozet:
        for i, (ad, puan, duzey) in enumerate([
                ("Ateşman", ozet.atesman, ozet.atesman_duzeyi),
                ("Çetinkaya-Uzun", ozet.cetinkaya_uzun, ozet.cetinkaya_uzun_duzeyi),
                ("Bezirci-Yılmaz", ozet.bezirci_yilmaz, ozet.bezirci_yilmaz_duzeyi)], start=1):
            _hucre(ws, r + i, 1, ad)
            _hucre(ws, r + i, 2, puan, number_format="0.0")
            _hucre(ws, r + i, 3, duzey)
        r += 4
    else:
        _hucre(ws, r + 1, 1, "Hesaplanamadı (skorlanabilen paragraf yok)")
        r += 2

    # Ölçülmüş başarı (geliştirme sırasında)
    r += 1
    _hucre(ws, r, 1, "Sistemin ölçülmüş başarısı (geliştirme sırasında)", yazi=_yazi(kalin=True, boyut=12))
    for i, (kriter, metin, kaynak) in enumerate(OLCULEN_BASARI, start=1):
        _hucre(ws, r + i, 1, kriter, alignment=Alignment(vertical="top"))
        _hucre(ws, r + i, 2, f"{metin} Kaynak: {kaynak}", alignment=Alignment(wrap_text=True, vertical="top"))
        ws.merge_cells(start_row=r + i, start_column=2, end_row=r + i, end_column=10)
        ws.row_dimensions[r + i].height = 30
    r += len(OLCULEN_BASARI) + 2

    # Nasıl kullanılır
    _hucre(ws, r, 1, "Nasıl kullanılır", yazi=_yazi(kalin=True, boyut=12))
    adimlar = [
        "1. Tespitler sayfasında başlıklardaki filtre oklarıyla kritere, önceliğe ya da sayfaya göre süzün.",
        "2. Her satırı kitapla karşılaştırın (PDF s. = PDF okuyucudaki sayfa; notlu PDF'te aynı yerde not var).",
        "3. Sarı 'Editör kararı' hücresinden seçin: Hata / Hata değil / Emin değilim. "
        "Gerekirse 'Editör notu'na yazın. Yalnız sarı hücreler doldurulur.",
        "   Örnek satır → İlgili metin: tıbba · Editör kararı: Hata değil · Editör notu: doğru yazım (tıp + -a)",
        "4. Bu sayfadaki sayılar ve isabet oranı kararlar girildikçe kendiliğinden güncellenir.",
        "Tespitler sistemin önerisidir, kesin hata değildir; son karar editöründür.",
    ]
    for i, a in enumerate(adimlar, start=1):
        _hucre(ws, r + i, 1, a)


def rapor_olustur(cikti_yolu, sonuclar: KitapSonuclari, kitap: str, sayfa_sayisi: int | None = None,
                  kapsam: str | None = None) -> dict:
    """Excel raporunu yazar. Döner: {kriter: satır sayısı}."""
    satirlar = tespit_satirlari(sonuclar)
    wb = Workbook()
    _ozet_sayfasi(wb.active, sonuclar, kitap, sayfa_sayisi, kapsam)
    _tespitler_sayfasi(wb.create_sheet(), satirlar)
    wb.calculation.fullCalcOnLoad = True  # formüller açılışta hesaplansın
    wb.save(cikti_yolu)
    return dict(Counter(s["Kriter"] for s in satirlar))


def editor_kararlari(yol) -> list[dict]:
    """Editörün doldurduğu rapordan satırlar: {kimlik, kriter, oncelik, karar, not}.
    Sütunlar başlık adından bulunur; editör satırları sıralamış olsa da olur."""
    wb = load_workbook(yol, read_only=True)
    try:  # salt okunur kitap dosyayı açık tutar: kapatılmazsa Windows dosyayı kilitli bırakır
        satirlar = list(wb["Tespitler"].iter_rows(values_only=True))
    finally:
        wb.close()
    baslik = {ad: i for i, ad in enumerate(satirlar[0]) if ad}
    sonuc = []
    for s in satirlar[1:]:
        if s[baslik["Kimlik"]] is None:
            continue
        karar = (s[baslik["Editör kararı"]] or "").strip()
        sonuc.append({"kimlik": s[baslik["Kimlik"]], "kriter": s[baslik["Kriter"]], "oncelik": s[baslik["Öncelik"]],
                      "karar": karar if karar in KARARLAR else None, "not": s[baslik["Editör notu"]] or ""})
    return sonuc


def isabet_ozeti(kararlar: list[dict]) -> dict:
    """{kriter: {"Hata": n, "Hata değil": n, "Emin değilim": n, "Bakılmadı": n, "isabet": oran ya da None}}"""
    ozet = defaultdict(Counter)
    for k in kararlar:
        ozet[k["kriter"]][k["karar"] or "Bakılmadı"] += 1
    sonuc = {}
    for kriter, say in ozet.items():
        payda = say["Hata"] + say["Hata değil"]
        sonuc[kriter] = {**{a: say[a] for a in (*KARARLAR, "Bakılmadı")},
                         "isabet": say["Hata"] / payda if payda else None}
    return sonuc


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Excel inceleme raporu / editör kararlarını okuma")
    ap.add_argument("pdf", type=Path, nargs="?")
    ap.add_argument("--sinif", type=int, help="Hedef sınıf (verilmezse kapaktan bulunur)")
    ap.add_argument("--hakem", action="store_true", help="Yazım tespitlerini yerel dil modeline danış (K25)")
    ap.add_argument("--oku", type=Path, help="Editörün doldurduğu raporu oku, isabet oranını yaz")
    arg = ap.parse_args()

    if arg.oku:
        for kriter, d in isabet_ozeti(editor_kararlari(arg.oku)).items():
            isabet = f"%{d['isabet'] * 100:.0f}" if d["isabet"] is not None else "-"
            print(f"{kriter}: Hata {d['Hata']}, Hata değil {d['Hata değil']}, Emin değilim {d['Emin değilim']}, "
                  f"bakılmadı {d['Bakılmadı']} → isabet {isabet}")
        return
    if arg.pdf is None:
        ap.error("PDF dosyası ya da --oku verilmeli")
    import pymupdf
    with pymupdf.open(arg.pdf) as belge:
        sayfa_sayisi = len(belge)
    sonuclar = sonuclari_topla(arg.pdf, hedef_sinif=arg.sinif, hakem=arg.hakem, ilerleme=print)
    cikti = arg.pdf.with_name(arg.pdf.stem + "_rapor.xlsx")
    sayilar = rapor_olustur(cikti, sonuclar, arg.pdf.name, sayfa_sayisi)
    print(f"-> {cikti}")
    for kriter, ad in KRITER_ADLARI.items():
        print(f"  {ad}: " + ("çalıştırılmadı" if sonuclar.tespitler[kriter] is None else f"{sayilar.get(ad, 0)} tespit"))


if __name__ == "__main__":
    main()
