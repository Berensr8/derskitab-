"""Notlu PDF: tespitleri kitabın kendi PDF'ine standart yorum notları olarak işler (Faz 2, K26).

Girdi : PDF dosyası (+ varsa veri klasöründeki çıkarma ve tutarlılık sonuçları)
Çıktı : <kitap>_notlu.pdf — kitabın kendisi (sayfalar ve sayfa numaraları değişmez), üzerinde:
  - Yazım     : hatalı kelimenin altında kırmızı dalgalı çizgi (Word'deki gibi)
  - Okunabilirlik: paragrafın çevresinde turuncu çerçeve (dilsel karmaşıklık uyarısı, K24)
  - Tutarlılık: çelişen iki cümle mor vurgulu; kenar boşluğunda "↔ s. 45" etiketine
                tıklayınca karşı cümleye gidilir
  - 1. sayfada özet notu, yer imlerinde (sol panel) kritere göre tespit listesi
Notlar PDF'in kendi yorum notlarıdır (metne çizilmez): Acrobat, Edge, Foxit gibi her
okuyucuda "Yorumlar" panelinde listelenir; editör yanıt yazabilir, "çözüldü" işaretleyebilir,
gizleyebilir. Kitabın metni değişmez.

Kullanım:
    python -m derskitabi.pdf_notlari veri/kitap.pdf [--sinif 6] [--hakem] [--dusuk-guven]
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

from .gorsellestir import _ham_kelimeler, cumle_dikdortgenleri
from .inceleyici import parca_kutulari, satirlari_birlestir, tutarlilik_kaydi_yukle
from .kayit import bloklari_yukle, tespitleri_yukle
from .kriterler import okunabilirlik, yazim
from .kriterler.okunabilirlik import cumlelere_bol
from .model import Blok, Tespit
from .pdf_cikarma import _OKUMA_AYARLARI, bloklari_cikar

YAZAR = "Ders Kitabı İnceleme Sistemi"
GOSTERIM_ESIGI = 0.5  # inceleyicideki gibi: altındakiler "düşük öncelik" (yazım hakemi, K25)
RENKLER = {"yazim": (0.85, 0.1, 0.1), "okunabilirlik": (1.0, 0.5, 0.0),
           "tutarlilik": (0.55, 0.25, 0.8), "dusuk": (0.6, 0.6, 0.6)}
TUTARLILIK_VURGUSU = (0.85, 0.72, 1.0)
KRITER_ADLARI = {"yazim": "Yazım ve dil", "okunabilirlik": "Dilsel karmaşıklık (okunabilirlik)",
                 "tutarlilik": "Bilgi tutarsızlığı"}
KURAL_ADLARI = {"noktalama_bosluk": "noktalamadan sonra boşluk", "bag_te_ta": "bağlaç de/da",
               "bag_de_da_uyum": "bağlaç de/da uyumu", "soru_eki_uyum": "soru eki uyumu",
               "ya_da": "ya da", "bitisik_ayri": "bitişik/ayrı yazım", "kelime_tekrari": "bağlaç tekrarı"}
UYARI = "Bu not sistemin önerisidir, kesin hata değildir; editör kontrolü gerekir."


def konum_metni(sayfa_no: int, basili: str | None) -> str:
    return f"PDF s. {sayfa_no}" + (f" / kitap s. {basili}" if basili else "")


def guven_metni(g: float) -> str:
    duzey = "yüksek" if g >= 0.75 else "orta" if g >= GOSTERIM_ESIGI else "düşük"
    return f"{duzey} ({str(round(g, 2)).replace('.', ',')})"


def _kisalt(metin: str, n: int = 45) -> str:
    metin = " ".join(metin.split())
    return metin if len(metin) <= n else metin[:n - 1].rstrip() + "…"


def _kutular(liste) -> list[pymupdf.Rect]:
    return [pymupdf.Rect(k) for k in liste]


def _not(annot, kriter: str, baslik: str, icerik: str, renk=None) -> None:
    annot.set_colors(stroke=renk or RENKLER[kriter])
    annot.set_info(title=YAZAR, subject=baslik, content=icerik)
    annot.update()


class _Sayfalar:
    """Sayfa başına kelime listesini bir kez okur (aynı sayfada birçok not olabilir) ve
    konan etiketleri tutar (etiketler birbirinin üstüne binmesin)."""

    def __init__(self, belge: pymupdf.Document):
        self.belge = belge
        self._kelimeler = {}
        self.etiketler = defaultdict(list)

    def dolu(self, no: int) -> list[pymupdf.Rect]:
        """Etiket konamayacak yerler: sayfadaki kelimeler ve önceki etiketler."""
        return [pymupdf.Rect(k[:4]) for k in self.kelimeler(no)] + self.etiketler[no]

    def sayfa(self, no: int) -> pymupdf.Page:
        return self.belge[no - 1]

    def kelimeler(self, no: int) -> list:
        if no not in self._kelimeler:
            self._kelimeler[no] = self.sayfa(no).get_text("words", flags=_OKUMA_AYARLARI)
        return self._kelimeler[no]


def _yazim_notu(s: _Sayfalar, t: Tespit, dusuk: bool) -> tuple[float, float]:
    sayfa = s.sayfa(t.sayfa_no)
    kutular = _kutular(parca_kutulari(_ham_kelimeler(s.kelimeler(t.sayfa_no), t.bbox), t.metin_parcasi or ""))
    tur = "kelime" if t.alt_tur == "morfoloji" else f"TDK kuralı: {KURAL_ADLARI.get(t.alt_tur, t.alt_tur)}"
    icerik = (f"{t.aciklama}\n\nKonum: {konum_metni(t.sayfa_no, t.basili_sayfa_no)}\n"
              f"Güven: {guven_metni(t.guven_skoru)}\n\n{UYARI}")
    renk = RENKLER["dusuk"] if dusuk else None
    if kutular:
        annot = sayfa.add_squiggly_annot(kutular)
    else:  # kelime sayfada bulunamadı (PDF okuma farkı): bütün blok işaretlenir
        kutular = [pymupdf.Rect(t.bbox) + (-2, -2, 2, 2)]
        annot = sayfa.add_rect_annot(kutular[0])
        annot.set_border(width=0.8, dashes=[2, 2])
    _not(annot, "yazim", f"Yazım ({tur})", icerik, renk)
    return kutular[0].x0, kutular[0].y0


def _okunabilirlik_notu(s: _Sayfalar, t: Tespit) -> tuple[float, float]:
    r = pymupdf.Rect(t.bbox) + (-3, -3, 3, 3)
    annot = s.sayfa(t.sayfa_no).add_rect_annot(r)
    annot.set_border(width=1.5)
    icerik = (f"{t.aciklama}\n\nEn uzun cümle: {t.metin_parcasi}\n\n"
              f"Konum: {konum_metni(t.sayfa_no, t.basili_sayfa_no)}\nGüven: {guven_metni(t.guven_skoru)}\n\n"
              "Not: Formüller cümle ve kelime uzunluğunu ölçer; sınıf düzeyini göstermez (K24). "
              "Bu bir dilsel karmaşıklık uyarısıdır: paragrafın sadeleştirilmesi düşünülebilir.\n\n" + UYARI)
    _not(annot, "okunabilirlik", "Dilsel karmaşıklık", icerik)
    return r.x0, r.y0


def cumle_kutulari(s: _Sayfalar, blok: Blok, cumle: str) -> list[pymupdf.Rect]:
    """Bloktaki bir cümlenin satır satır dikdörtgenleri; bulunamazsa boş liste."""
    cumleler = cumlelere_bol(blok.metin)
    kutular = cumle_dikdortgenleri(s.kelimeler(blok.sayfa_no), blok) if cumle in cumleler else None
    return _kutular(satirlari_birlestir(kutular[cumleler.index(cumle)])) if kutular else []


ETIKET_GENISLIGI, ETIKET_YUKSEKLIGI = 38, 11


def etiket_kutusu(sayfa_genisligi: float, bbox, ust: float, dolu=()) -> pymupdf.Rect:
    """"↔ s. 45" etiketinin yeri: kitabın yazısının ve önceki etiketlerin (dolu) üstüne binmeyen
    ilk konum. Sıra: bloğun boşluğu geniş yanı, öbür yanı, sayfanın sağ/sol kenarı; aynı hizada
    yer yoksa birkaç satır aşağı/yukarı. Hiç yer yoksa bloğun yanı (kenar boşlukları da yazı dolu)."""
    g, y = ETIKET_GENISLIGI, ETIKET_YUKSEKLIGI
    sag, sol = min(bbox[2] + 3, sayfa_genisligi - g - 2), max(bbox[0] - 3 - g, 2)
    xler = [sag, sol] if sayfa_genisligi - bbox[2] >= bbox[0] else [sol, sag]
    xler += [sayfa_genisligi - g - 2, 2]
    for dy in (0, y, 2 * y, -y, 3 * y):
        for x in xler:
            r = pymupdf.Rect(x, ust + dy, x + g, ust + dy + y)
            if not any(r.intersects(d) for d in dolu):
                return r
    return pymupdf.Rect(xler[0], ust, xler[0] + g, ust + y)


def _celiski_tarafi(s: _Sayfalar, blok: Blok, cumle: str, karsi: dict, icerik: str) -> tuple[float, float]:
    """Bir cümleyi vurgular ve kenar boşluğuna karşı cümleye giden etiket koyar."""
    sayfa = s.sayfa(blok.sayfa_no)
    kutular = cumle_kutulari(s, blok, cumle)
    if kutular:
        annot = sayfa.add_highlight_annot(kutular)
        _not(annot, "tutarlilik", "Bilgi tutarsızlığı", icerik, TUTARLILIK_VURGUSU)
    else:  # cümle sayfada bulunamadı: bütün blok çerçevelenir
        kutular = [pymupdf.Rect(blok.bbox) + (-2, -2, 2, 2)]
        annot = sayfa.add_rect_annot(kutular[0])
        annot.set_border(width=1.2, dashes=[3, 2])
        _not(annot, "tutarlilik", "Bilgi tutarsızlığı", icerik)
    etiket = etiket_kutusu(sayfa.rect.width, blok.bbox, kutular[0].y0, s.dolu(blok.sayfa_no))
    s.etiketler[blok.sayfa_no].append(etiket)
    yazi = sayfa.add_freetext_annot(etiket, f"↔ s. {karsi['basili'] or karsi['sayfa_no']}", fontsize=7,
                                    text_color=RENKLER["tutarlilik"], fill_color=(1, 1, 1),
                                    align=pymupdf.TEXT_ALIGN_CENTER)
    # FreeText'te "content" görünen yazının kendisi: yalnız yazar ve konu verilir
    yazi.set_info(title=YAZAR, subject="Bilgi tutarsızlığı: karşı cümleye gitmek için tıklayın")
    yazi.update()
    sayfa.insert_link({"kind": pymupdf.LINK_GOTO, "from": etiket, "page": karsi["sayfa_no"] - 1,
                       "to": pymupdf.Point(karsi["x"], max(karsi["y"] - 20, 0))})
    return kutular[0].x0, kutular[0].y0


def karsi_cumle(t: Tespit, kayit: list[dict] | None) -> str | None:
    """Tutarlılık tespitinin diğer tarafındaki cümle (aday kaydından)."""
    if not t.ilgili_konumlar:
        return None
    hedef = tuple(t.ilgili_konumlar[0])
    for k in kayit or []:
        if (k["a"]["metin"] == t.metin_parcasi and (k["a"]["sayfa_no"], k["a"]["blok_no"]) == (t.sayfa_no, t.blok_no)
                and (k["b"]["sayfa_no"], k["b"]["blok_no"]) == hedef):
            return k["b"]["metin"]
    return None


def _tutarlilik_notu(s: _Sayfalar, t: Tespit, bloklar: dict, kayit) -> tuple[float, float]:
    a = bloklar.get((t.sayfa_no, t.blok_no)) or Blok(t.sayfa_no, t.blok_no, t.bbox, "", t.basili_sayfa_no)
    b = bloklar.get(tuple(t.ilgili_konumlar[0])) if t.ilgili_konumlar else None
    icerik = (f"{t.aciklama}\n\nGüven: {guven_metni(t.guven_skoru)} "
              "(1,0: iki dil modeli de çelişki dedi; 0,5: yalnız gemma4)\n\n" + UYARI)
    if b is None:  # karşı taraf bilinmiyor: yalnız bu cümle
        r = pymupdf.Rect(t.bbox) + (-2, -2, 2, 2)
        _not(s.sayfa(t.sayfa_no).add_rect_annot(r), "tutarlilik", "Bilgi tutarsızlığı", icerik)
        return r.x0, r.y0
    b_cumle = karsi_cumle(t, kayit) or ""  # bulunamazsa karşı blok çerçevelenir
    # Önce iki tarafın konumu bulunur: kenardaki etiketler birbirine bağlanır
    a_kutu = (cumle_kutulari(s, a, t.metin_parcasi) or [pymupdf.Rect(a.bbox)])[0]
    b_kutu = (cumle_kutulari(s, b, b_cumle) or [pymupdf.Rect(b.bbox)])[0]
    konum_a = {"sayfa_no": a.sayfa_no, "basili": a.basili_sayfa_no, "x": a_kutu.x0, "y": a_kutu.y0}
    konum_b = {"sayfa_no": b.sayfa_no, "basili": b.basili_sayfa_no, "x": b_kutu.x0, "y": b_kutu.y0}
    nokta = _celiski_tarafi(s, a, t.metin_parcasi, konum_b, icerik)
    _celiski_tarafi(s, b, b_cumle, konum_a,
                    f"Bu {'cümle' if b_cumle else 'paragraf'}, {konum_metni(a.sayfa_no, a.basili_sayfa_no)} "
                    f"sayfasındaki şu cümleyle çelişiyor olabilir: \"{t.metin_parcasi}\"\n\n" + icerik)
    return nokta


def _yer_imi_basligi(t: Tespit, bloklar: dict) -> str:
    yer = f"s. {t.basili_sayfa_no or t.sayfa_no}"
    if t.kriter == "yazim" and t.alt_tur == "morfoloji":
        return f"{yer}: {t.metin_parcasi}"
    if t.kriter == "yazim":  # kural kesiti kelime ortasından başlayabilir: kuralın adı + noktalamalı kelime
        kelimeler = (t.metin_parcasi or "").split()
        isaretli = [k for k in kelimeler if any(c in k for c in ".,;:!?")] or kelimeler[1:-1] or kelimeler
        return f"{yer}: {KURAL_ADLARI.get(t.alt_tur, t.alt_tur)} — {_kisalt(' '.join(isaretli[:2]), 30)}"
    if t.kriter == "tutarlilik" and t.ilgili_konumlar:
        b = bloklar.get(tuple(t.ilgili_konumlar[0]))
        karsi = (b.basili_sayfa_no or b.sayfa_no) if b else t.ilgili_konumlar[0][0]
        return f"{yer} ↔ s. {karsi}: {_kisalt(t.metin_parcasi or '')}"
    metin = bloklar[(t.sayfa_no, t.blok_no)].metin if (t.sayfa_no, t.blok_no) in bloklar else ""
    return f"{yer}: {_kisalt(metin)}"


def notlari_ekle(belge: pymupdf.Document, bloklar: list[Blok], tespitler: dict[str, list[Tespit] | None],
                 tutarlilik_kaydi: list[dict] | None = None, dusuk_guven: bool = False,
                 kapsam: str | None = None) -> dict:
    """Tespitleri belgeye not olarak ekler; özet notu ve yer imlerini yazar.

    tespitler: {"yazim": [...], "okunabilirlik": [...], "tutarlilik": [...] ya da None (çalıştırılmadı)}
    dusuk_guven: güveni 0,5'in altındaki yazım tespitleri de (gri) eklensin mi.
    kapsam: kitabın yalnız bir kısmı incelendiyse özet notuna yazılacak açıklama.
    Döner: {kriter: eklenen not sayısı, "dusuk_atlanan": n}
    """
    blok_dizini = {(b.sayfa_no, b.blok_no): b for b in bloklar}
    s = _Sayfalar(belge)
    sayac, atlanan, yer_imleri = Counter(), 0, defaultdict(list)
    for kriter in ("yazim", "okunabilirlik", "tutarlilik"):
        for t in sorted(tespitler.get(kriter) or [], key=lambda t: (t.sayfa_no, t.bbox[1], t.bbox[0])):
            dusuk = t.guven_skoru < GOSTERIM_ESIGI
            if dusuk and not dusuk_guven:
                atlanan += 1
                continue
            if kriter == "yazim":
                x, y = _yazim_notu(s, t, dusuk)
            elif kriter == "okunabilirlik":
                x, y = _okunabilirlik_notu(s, t)
            else:
                x, y = _tutarlilik_notu(s, t, blok_dizini, tutarlilik_kaydi)
            sayac[kriter] += 1
            baslik = _yer_imi_basligi(t, blok_dizini) + (" (düşük öncelik)" if dusuk else "")
            yer_imleri[kriter].append((baslik, t.sayfa_no, x, y))
    _ozet_notu(belge, tespitler, sayac, atlanan, dusuk_guven, kapsam)
    _yer_imlerini_yaz(belge, tespitler, yer_imleri)
    return {**{k: sayac[k] for k in KRITER_ADLARI}, "dusuk_atlanan": atlanan}


def _sayi_metni(kriter: str, tespitler: dict, sayac: Counter) -> str:
    if tespitler.get(kriter) is None:
        return "çalıştırılmadı"
    return f"{sayac[kriter]} not" if sayac[kriter] else "bulunmadı"


def _ozet_notu(belge, tespitler, sayac, atlanan, dusuk_guven, kapsam=None) -> None:
    satirlar = [f"{YAZAR} — otomatik inceleme notları", ""] + ([kapsam, ""] if kapsam else [])
    satirlar += [f"• {ad}: {_sayi_metni(k, tespitler, sayac)}" for k, ad in KRITER_ADLARI.items()]
    if atlanan:
        satirlar.append(f"• Düşük öncelikli {atlanan} yazım tespiti eklenmedi (dil modeli muhtemelen "
                        "doğru dedi; eklemek için --dusuk-guven).")
    elif dusuk_guven:
        satirlar.append("• Düşük öncelikli yazım tespitleri gri renkte eklendi.")
    satirlar += ["", "Renkler: kırmızı dalgalı çizgi = yazım, turuncu çerçeve = dilsel karmaşıklık, "
                 "mor vurgu = çelişen cümleler (kenardaki ↔ etiketi karşı cümleye götürür).",
                 "Tüm notlar okuyucunun Yorumlar panelinde, kritere göre liste Yer İmleri panelinde.",
                 "", UYARI]
    sayfa = belge[0]
    annot = sayfa.add_text_annot((sayfa.rect.width - 28, 8), "\n".join(satirlar), icon="Comment")
    annot.set_info(title=YAZAR, subject="İnceleme özeti")
    annot.set_colors(stroke=(1.0, 0.85, 0.2))
    annot.update()


def _yer_imlerini_yaz(belge, tespitler, yer_imleri) -> None:
    """Kitabın kendi yer imleri korunur; sonuna "İnceleme notları" bölümü eklenir.
    Kitabın yer imleri sayfa numarasıyla korunur: ayrıntılı biçim (adlandırılmış hedefler)
    yeniden yazılınca bozuluyordu (sayfa -1)."""
    toc = belge.get_toc(simple=True)
    toplam = sum(len(v) for v in yer_imleri.values())
    toc.append([1, f"İnceleme notları ({toplam})", 1])
    for kriter, ad in KRITER_ADLARI.items():
        liste = yer_imleri.get(kriter, [])
        toc.append([2, f"{ad} ({_sayi_metni(kriter, tespitler, Counter({kriter: len(liste)}))})",
                    liste[0][1] if liste else 1])
        for baslik, sayfa_no, x, y in liste:
            toc.append([3, baslik, sayfa_no, {"kind": pymupdf.LINK_GOTO, "page": sayfa_no - 1,
                                              "to": pymupdf.Point(x, max(y - 20, 0)), "zoom": 0}])
    belge.set_toc(toc)


def notlu_pdf_olustur(pdf_yolu, cikti_yolu, bloklar: list[Blok] | None = None, hedef_sinif: int | None = None,
                      yazim_tespitleri: list[Tespit] | None = None, okunabilirlik_tespitleri: list[Tespit] | None = None,
                      tutarlilik_tespitleri: list[Tespit] | None = None, tutarlilik_kaydi: list[dict] | None = None,
                      hakem: bool = False, dusuk_guven: bool = False, kapsam: str | None = None,
                      ilerleme=None) -> dict:
    """Verilmeyen sonuçlar burada hesaplanır (yazım, okunabilirlik) ya da PDF'in yanındaki dosyadan
    okunur (tutarlılık — yerel modeller gerekir, uzun sürer; dosya yoksa "çalıştırılmadı")."""
    yaz = ilerleme or (lambda _m: None)
    pdf_yolu = Path(pdf_yolu)
    kok = pdf_yolu.with_suffix("")
    if bloklar is None:
        kayitli = Path(f"{kok}_bloklar.json")
        bloklar = bloklari_yukle(kayitli) if kayitli.exists() else bloklari_cikar(pdf_yolu)
    if okunabilirlik_tespitleri is None:
        try:
            okunabilirlik_tespitleri = okunabilirlik.analiz_et(bloklar, hedef_sinif)[1]
        except ValueError:  # skorlanabilen paragraf yok
            okunabilirlik_tespitleri = []
    if yazim_tespitleri is None:
        yaz("Yazım denetimi…")
        yazim_tespitleri = yazim.analiz_et(bloklar)
        if hakem:
            from .kriterler.yazim_hakem import hakemle
            onbellek_yolu = pdf_yolu.with_name("yazim_hakem_onbellek.json")
            onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
            try:
                yazim_tespitleri = hakemle(yazim_tespitleri, bloklar, onbellek=onbellek, ilerleme=yaz)
            finally:
                onbellek_yolu.write_text(json.dumps(onbellek, ensure_ascii=False), encoding="utf-8")
    if tutarlilik_tespitleri is None:
        yol = Path(f"{kok}_tutarlilik_tespitler.json")
        tutarlilik_tespitleri = tespitleri_yukle(yol) if yol.exists() else None
    if tutarlilik_kaydi is None and tutarlilik_tespitleri:
        tutarlilik_kaydi = tutarlilik_kaydi_yukle(pdf_yolu)

    yaz("Notlar PDF'e işleniyor…")
    with pymupdf.open(pdf_yolu) as belge:
        sonuc = notlari_ekle(belge, bloklar, {"yazim": yazim_tespitleri, "okunabilirlik": okunabilirlik_tespitleri,
                                              "tutarlilik": tutarlilik_tespitleri},
                             tutarlilik_kaydi, dusuk_guven, kapsam)
        belge.save(cikti_yolu, garbage=1)
    return sonuc


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Tespitleri kitabın PDF'ine yorum notu olarak işler")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--sinif", type=int, help="Hedef sınıf (verilmezse kapaktan bulunur)")
    ap.add_argument("--hakem", action="store_true", help="Yazım tespitlerini yerel dil modeline danış (K25)")
    ap.add_argument("--dusuk-guven", action="store_true", help="Düşük öncelikli yazım tespitlerini de (gri) ekle")
    arg = ap.parse_args()

    cikti = arg.pdf.with_name(arg.pdf.stem + "_notlu.pdf")
    sonuc = notlu_pdf_olustur(arg.pdf, cikti, hedef_sinif=arg.sinif, hakem=arg.hakem,
                              dusuk_guven=arg.dusuk_guven, ilerleme=print)
    print(f"-> {cikti} ({cikti.stat().st_size / 1e6:.1f} MB)")
    for k, ad in KRITER_ADLARI.items():
        print(f"  {ad}: {sonuc[k]} not")
    if sonuc["dusuk_atlanan"]:
        print(f"  Düşük öncelikli {sonuc['dusuk_atlanan']} yazım tespiti eklenmedi (--dusuk-guven ile eklenir)")
    print("Dosyayı herhangi bir PDF okuyucuda açın; notlar Yorumlar panelinde, liste Yer İmleri panelinde.")


if __name__ == "__main__":
    main()
