"""Etkileşimli PDF inceleyici: sistemin kitabı nasıl okuduğunu tarayıcıda gösterir.

Girdi : PDF dosyası
Çıktı : <kitap>_inceleme.html (tek dosya; çift tıklayınca tarayıcıda açılır, sunucu gerekmez)
  - Sayfa görüntüsü üzerinde bloklar (renk = tür). Bloğa tıklayınca yan panelde:
    neden bu türde sayıldığı, cümleleri, kelimelerin hece sayıları, formül hesabının
    adımları ve varsa okunabilirlik tespiti.
  - Yazım denetimi adım adım: PDF okuma kontrolü, her kelimede iki aracın kararı ve
    atlanma sebebi (renkli), TDK kurallarının bu blokta sonucu.
  - Bilgi tutarsızlığı: çelişen iki cümle (mor), karşı sayfaya geçiş; sistemin üç adımı
    (bge-m3 benzerliği, gemma4 hızlı kararı, iki modelin açıklamalı kararı) ve bloğun
    karşılaştırıldığı diğer cümleler. Veri <kitap>_tutarlilik_adaylar.json'dan okunur
    (tutarlılık önceden çalıştırılmalı; yoksa sekme görünmez).
  - Yan panelde sayfadaki tüm bloklar listelenir (küçük kutulara listeden ulaşılır).

Kullanım:
    python -m derskitabi.inceleyici veri/kitap.pdf [--sayfalar 10-35] [--sinif 6]

Bilgi gorsellestir.blok_raporu() ile üretilir (işaretli PDF ile aynı kaynak, K12).
"""

import argparse
import base64
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

from .gorsellestir import _ham_kelimeler, blok_raporu, cumle_dikdortgenleri, sayfa_araligi_coz
from .kriterler.okunabilirlik import cumlelere_bol
from .kriterler import dusuk_oncelik, okunabilirlik, tutarlilik, yazim
from .model import Blok, Tespit
from .pdf_cikarma import _OKUMA_AYARLARI, bloklari_cikar

SABLON = Path(__file__).parent / "sablonlar" / "inceleyici.html"
GORUNTU_DPI = 110
# Yazım iz kaydında düşük önceliğe inen kelimenin notu (kitap ipuçları, K28, K29)
IPUCU_ACIKLAMALARI = {
    "alıntı içinde": "alıntı metin: yazarın kendi yazımı ya da eski yazım olabilir (düşük öncelik)",
    "terim": "kitabın kendi terimi: sözlüğünde açıklanmış ya da italik yazılmış (düşük öncelik)",
    "PDF okuma parçası": "PDF okuma parçası: kelime metin çıkarılırken parçalanmış (düşük öncelik)"}


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


def parca_kutulari(ham: list[tuple[pymupdf.Rect, str]], parca: str) -> list[list[float]]:
    """Yazım tespitindeki metin parçasının sayfadaki kelime kutuları (kırmızı çizgi için).

    Morfoloji tespitinde parça tek kelimedir; kural tespitinde birkaç kelimelik bir
    kesittir ("katlandı.Takım arkada") — noktalama içeren ya da tam kelime olan parçalar aranır.
    """
    adaylar = [p.strip("…") for p in parca.replace("’", "'").split()]
    adaylar = [p for p in adaylar if len(p) >= 2]
    noktalamali = [p for p in adaylar if any(c in p for c in ".,;:!?")]
    kutular = []
    for aday in (noktalamali or adaylar):
        for r, k in ham:
            k = k.replace("’", "'")
            if aday == k or (len(aday) >= 4 and (aday in k or (len(k) >= 4 and k in aday))):
                kutular.append([round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)])
                break
    return kutular


def _yazim_verisi(t: Tespit, ham) -> dict:
    return {"alt_tur": t.alt_tur, "parca": t.metin_parcasi, "aciklama": t.aciklama,
            "guven": t.guven_skoru, "kutular": parca_kutulari(ham, t.metin_parcasi)}


def yazim_baglami(bloklar: list[Blok]) -> dict:
    """Bütün sayfalar için bir kez hazırlanan bilgiler: araçlar ve kitaptaki kelime sayıları."""
    return {"denetciler": yazim.varsayilan_denetciler(),
            "kitap_kelimeleri": yazim.kitap_kelime_sayilari(bloklar)}


def yazim_izi(blok: Blok, blok_tespitleri: list[Tespit], baglam: dict, ham) -> dict | None:
    """Yazım denetiminin bu blokta adım adım ne yaptığı (inceleyicideki "adım adım" bölümü).

    Kelimelerin son durumu:
      gecerli  iki araç da tanıdı            supheli  yalnız biri tanımadı (güven 0,5)
      hata     ikisi de tanımadı (güven 1)   atlandi  sahte hata önlemi (sebebiyle)
      terim    kitaba özel terim (K15)       okuma    PDF okuma sorunu (blok/sayfa düzeyi)
    Kararlar yazim.kelime_denetimi() içinden gelir; burada yeniden verilmez.
    """
    if blok.tur not in ("paragraf", "kisa"):
        return None
    iz = {}
    yazim.kelime_denetimi(blok, baglam["denetciler"], iz=iz)
    hatali = {t.metin_parcasi: t.guven_skoru for t in blok_tespitleri if t.alt_tur == "morfoloji"}
    ipuclu = {t.metin_parcasi: dusuk_oncelik.sebep(t) for t in blok_tespitleri if dusuk_oncelik.sebep(t)}
    kelimeler = []
    for k in iz["kelimeler"]:
        kucuk = yazim.tr_kucuk(k["kelime"])
        d = {"k": k["kelime"], "st": k["starlang"], "zb": k["zemberek"]}
        if k["starlang"] and k["zemberek"]:
            d["d"] = "gecerli"
        elif k["kelime"] in hatali:
            g = hatali[k["kelime"]]
            if k["kelime"] in ipuclu:  # kitap ipuçları (K28, K29)
                d["d"], d["not"] = "atlandi", IPUCU_ACIKLAMALARI[ipuclu[k["kelime"]]]
            elif g < 0.5:  # yazım hakemi (K25): muhtemelen doğru, düşük öncelik
                d["d"], d["not"] = "atlandi", "dil modeli muhtemelen doğru yazıldığını söyledi (düşük öncelik)"
            else:
                d["d"] = "hata" if g >= 0.75 else "supheli"
        elif iz["blok_durumu"] != "denetlendi":
            d["d"] = "okuma"
        elif k["sebep"]:
            d["d"], d["not"] = "atlandi", k["sebep"]
        elif terim := yazim.kitaba_ozel_terimler({kucuk}, baglam["kitap_kelimeleri"],
                                                  baglam["denetciler"][0]):
            d["d"], d["not"] = "terim", terim[kucuk]
        else:
            d["d"] = "okuma"  # sayfa düzeyinde düşmüş harf (yazim.analiz_et)
        if d["d"] != "gecerli":
            d["kitapta"] = baglam["kitap_kelimeleri"][kucuk]
            d["kutular"] = parca_kutulari(ham, k["kelime"])
        kelimeler.append(d)
    return {
        "durum": iz["blok_durumu"],
        "uzun_kelime": iz.get("uzun_kelime", 0),
        "ikisi_gecersiz": iz.get("ikisi_gecersiz", 0),
        "dusmus_harf": iz.get("dusmus_harf", 0),
        "kelimeler": kelimeler,
        "kurallar": Counter(t.alt_tur for t in blok_tespitleri if t.alt_tur != "morfoloji"),
    }


TUTARLILIK_BLOK_SINIRI = 15  # bir blokta gösterilen en fazla karşılaştırma (dosya büyümesin)


def tutarlilik_kaydi_yukle(pdf_yolu) -> list[dict] | None:
    """tutarlilik.py'nin yazdığı aday kaydı (her aday çiftin bütün kararları); yoksa None."""
    yol = Path(pdf_yolu).with_name(Path(pdf_yolu).stem + "_tutarlilik_adaylar.json")
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else None


def tutarlilik_bloklari(kayit: list[dict]) -> dict:
    """{(sayfa, blok): [karşılaştırma, …]} — her aday çift iki tarafının bloğunda da görünür.
    Sıra: tespitler (güvene göre), sonra hızlı turun şüphelendikleri, sonra benzerlik."""
    dizin = defaultdict(list)
    for k in kayit:
        for ben, karsi in (("a", "b"), ("b", "a")):
            dizin[(k[ben]["sayfa_no"], k[ben]["blok_no"])].append({
                "ben": k[ben]["metin"],
                "karsi": {"metin": k[karsi]["metin"], "sayfa_no": k[karsi]["sayfa_no"],
                          "blok_no": k[karsi]["blok_no"], "basili": k[karsi].get("basili_sayfa_no")},
                "benzerlik": k["benzerlik"], "hizli": k["hizli"],
                "hakem": k.get("hakem"), "ikinci": k.get("ikinci_gorus"), "guven": k.get("guven"),
            })
    for liste in dizin.values():
        liste.sort(key=lambda x: (-(x["guven"] or 0), x["hizli"] != "celiski", -x["benzerlik"]))
    return dizin


def _tutarlilik_verisi(b: Blok, karsilastirmalar: list[dict], cumle_kutulari) -> list[dict]:
    cumleler = cumlelere_bol(b.metin)
    sonuc = []
    for k in karsilastirmalar[:TUTARLILIK_BLOK_SINIRI]:
        d = dict(k)
        if k["guven"] and cumle_kutulari and k["ben"] in cumleler:  # çelişkili cümle sayfada vurgulanır
            d["kutular"] = satirlari_birlestir(cumle_kutulari[cumleler.index(k["ben"])])
        sonuc.append(d)
    return sonuc


def sayfa_verisi(sayfa: pymupdf.Page, bloklar: list[Blok], tespitler: dict,
                 yazim_tespitleri: dict | None = None, baglam: dict | None = None,
                 tutarlilik: dict | None = None) -> dict:
    goruntu = sayfa.get_pixmap(dpi=GORUNTU_DPI).tobytes("jpeg", jpg_quality=80)
    kelimeler = sayfa.get_text("words", flags=_OKUMA_AYARLARI)
    yazim_tespitleri = yazim_tespitleri or {}
    veri_bloklari = []
    for b in bloklar:
        cumleler = cumle_dikdortgenleri(kelimeler, b) if b.tur == "paragraf" else None
        yazim_listesi = yazim_tespitleri.get((b.sayfa_no, b.blok_no), [])
        ham = _ham_kelimeler(kelimeler, b.bbox) if (yazim_listesi or baglam) else []
        veri_bloklari.append({
            "bbox": [round(v, 1) for v in b.bbox],
            "rapor": blok_raporu(b),
            "cumle_kutulari": [satirlari_birlestir(c) for c in cumleler] if cumleler else [],
            "tespit": _tespit_verisi(tespitler.get((b.sayfa_no, b.blok_no))),
            "yazim": [_yazim_verisi(t, ham) for t in yazim_listesi],
            "yazim_izi": yazim_izi(b, yazim_listesi, baglam, ham) if baglam else None,
            "tutarlilik": (_tutarlilik_verisi(b, tutarlilik.get((b.sayfa_no, b.blok_no), []), cumleler)
                           if tutarlilik is not None and b.tur == "paragraf" else None),
        })
    return {
        "no": sayfa.number + 1,
        "basili": bloklar[0].basili_sayfa_no if bloklar else None,
        "genislik": round(sayfa.rect.width, 1),
        "yukseklik": round(sayfa.rect.height, 1),
        "goruntu": "data:image/jpeg;base64," + base64.b64encode(goruntu).decode("ascii"),
        "bloklar": veri_bloklari,
    }


def _test_modu_hazirla(pdf_yolu, bloklar: list[Blok], set_adi: str):
    """Kilitli test setinin (K20) bu kitaba ait maddelerini bloklara uygular ve değerlendirmenin
    kaydettiği aday kaydını okur. Eklenen cümleler PDF görüntüsünde yoktur; inceleyici bunu
    sayfanın başında açıkça yazar."""
    from .degerlendirme import celiskileri_uygula, set_yukle, test_modu_kaydi_yolu
    kitap = Path(pdf_yolu).stem
    ogeler = [o for o in set_yukle() if o["set"] == set_adi and o["kitap"] == kitap]
    if not ogeler:
        raise ValueError(f"Test setinde '{kitap}' kitabı için '{set_adi}' maddesi yok.")
    kayit_yolu = test_modu_kaydi_yolu(kitap, set_adi)
    if not kayit_yolu.exists():
        raise ValueError(f"{kayit_yolu.name} yok: önce 'python -m derskitabi.degerlendirme --set {set_adi}' çalıştırın.")
    sayfalar = sorted({k["sayfa_no"] for o in ogeler for k in o["kaynaklar"]} | {o["hedef"]["sayfa_no"] for o in ogeler})
    bilgi = {"set": set_adi, "madde_sayisi": len(ogeler), "eklenenler": [o["hedef"]["yeni"] for o in ogeler]}
    return (celiskileri_uygula(bloklar, ogeler), json.loads(kayit_yolu.read_text(encoding="utf-8")),
            bilgi, sayfalar)


def inceleme_html_olustur(pdf_yolu, cikti_yolu, sayfalar: list[int] | None = None,
                          hedef_sinif: int | None = None, bloklar: list[Blok] | None = None,
                          analiz: tuple | None = None,
                          yazim_tespitleri: list[Tespit] | None = None,
                          tutarlilik_kaydi: list[dict] | None = None, test_modu: str | None = None) -> None:
    """bloklar, analiz (ozet, tespitler) ve yazım tespitleri önceden hesaplandıysa
    verilebilir (demo.py); verilmezse burada hesaplanır. Tutarlılık burada hesaplanmaz
    (yerel modeller gerekir, uzun sürer): verilmezse PDF'in yanındaki aday kaydı okunur."""
    if bloklar is None:
        bloklar = bloklari_cikar(pdf_yolu)
    test_bilgisi = None
    if test_modu:  # K20 test setindeki çelişkiler eklenmiş metinle (gösterim için)
        bloklar, tutarlilik_kaydi, test_bilgisi, varsayilan_sayfalar = _test_modu_hazirla(pdf_yolu, bloklar, test_modu)
        sayfalar = sayfalar or varsayilan_sayfalar
    if analiz is None:
        try:
            analiz = okunabilirlik.analiz_et(bloklar, hedef_sinif)
        except ValueError:  # skorlanabilen paragraf yok
            analiz = (None, [])
    ozet, tespit_listesi = analiz
    ozet_verisi = ozet.sozluge() if ozet else None
    tespitler = {(t.sayfa_no, t.blok_no): t for t in tespit_listesi}

    with pymupdf.open(pdf_yolu) as belge:
        secili = sayfalar or list(range(1, len(belge) + 1))
        if yazim_tespitleri is None:
            secili_kume = set(secili)
            yazim_tespitleri = yazim.analiz_et([b for b in bloklar if b.sayfa_no in secili_kume],
                                               kitap_bloklari=bloklar)
            # test modunda metin değiştirilmiş: yazı biçimleri PDF ile eşleşmez, yalnız metin ipuçları
            yazim_tespitleri = dusuk_oncelik.isaretle(None if test_modu else pdf_yolu, bloklar, yazim_tespitleri)
        yazim_bloklari = defaultdict(list)
        for t in yazim_tespitleri:
            yazim_bloklari[(t.sayfa_no, t.blok_no)].append(t)
        baglam = yazim_baglami(bloklar)
        if tutarlilik_kaydi is None:
            tutarlilik_kaydi = tutarlilik_kaydi_yukle(pdf_yolu)
        tut_bloklari = tutarlilik_bloklari(tutarlilik_kaydi) if tutarlilik_kaydi is not None else None
        sayfa_listesi = [
            sayfa_verisi(belge[no - 1], [b for b in bloklar if b.sayfa_no == no], tespitler,
                         yazim_bloklari, baglam, tut_bloklari)
            for no in secili
        ]

    veri = {
        "kitap": Path(pdf_yolu).name,
        "ozet": ozet_verisi,
        "toplam_tespit": len(tespit_listesi),
        "toplam_yazim": sum(len(v) for k, v in yazim_bloklari.items() if k[0] in set(secili)),
        "min_cumle": okunabilirlik.MIN_CUMLE,
        "tutarlilik_var": tutarlilik_kaydi is not None,
        "test_modu": test_bilgisi,
        "toplam_tutarlilik": sum(1 for k in (tutarlilik_kaydi or []) if k.get("guven")
                                 and (k["a"]["sayfa_no"] in set(secili) or k["b"]["sayfa_no"] in set(secili))),
        "tutarlilik_esikleri": list(tutarlilik.KOMSU_ESIKLERI),
        "yazim_esikleri": {"okuma_orani": yazim.OKUMA_SORUNU_ORANI, "blok_min": yazim.BLOK_MIN_KELIME,
                           "dusmus_harf": yazim.DUSMUS_HARF_ESIGI, "terim": yazim.TERIM_TEKRAR_ESIGI},
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
    ap.add_argument("--test-modu", nargs="?", const="gelistirme", choices=("gelistirme", "test"),
                    help="Test setindeki bilerek eklenmiş çelişkilerle göster (sayfa verilmezse ilgili sayfalar)")
    arg = ap.parse_args()

    with pymupdf.open(arg.pdf) as belge:
        sayfa_sayisi = len(belge)
    sayfalar = sayfa_araligi_coz(arg.sayfalar, sayfa_sayisi) if arg.sayfalar else None
    ek = "_test_modu" if arg.test_modu else ""
    cikti = arg.pdf.with_name(arg.pdf.stem + ek + "_inceleme.html")
    inceleme_html_olustur(arg.pdf, cikti, sayfalar, arg.sinif, test_modu=arg.test_modu)
    boyut = cikti.stat().st_size / 1e6
    print(f"{len(sayfalar) if sayfalar else 'ilgili'} sayfa -> {cikti} ({boyut:.1f} MB)")
    print("Dosyaya çift tıklayarak tarayıcıda açabilirsiniz.")


if __name__ == "__main__":
    main()
