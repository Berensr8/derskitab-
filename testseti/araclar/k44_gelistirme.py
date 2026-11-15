"""K44 yazım ve kesme iyileştirmeleri geliştirme ölçümü.

Bu betik K44'teki tüm bölümlerin (eski metin sayfası ipucu, öncelik sırası, 9 yeni kural,
kesme işareti '-ce' kişi adı istisnası) etkisini mevcut kitaplar ve geliştirme/doğrulama
setleri üzerinde ölçer.

UYARI: Bu sayılar geliştirme verisidir; kurallar bu hatalara bakılarak yazıldı.
Gerçek etki K45'te ölçülecek.
"""

import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import pymupdf

BEKLENEN_PYMUPDF = "1.28.2"
if pymupdf.__version__ != BEKLENEN_PYMUPDF:
    sys.exit(
        f"HATA: PyMuPDF sürümü {pymupdf.__version__}; beklenen: {BEKLENEN_PYMUPDF}. "
        "Lütfen D:\\derskitabı\\.venv\\Scripts\\python.exe kullanın."
    )

PROJE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJE))
sys.stdout.reconfigure(encoding="utf-8")

from derskitabi import degerlendirme_yazim  # noqa: E402
from derskitabi.kayit import bloklari_yukle  # noqa: E402
from derskitabi.kriterler import alinti, dusuk_oncelik, kesme, yazim, yazim_hakem  # noqa: E402
from derskitabi.model import Tespit  # noqa: E402

KITAPLAR_8 = [
    "biyoloji9", "biyoloji10", "biyoloji11", "matematik11",
    "turkdili9", "turkdili10", "turkdili11", "turkdili12",
]
KITAPLAR_9 = ["kitap"] + KITAPLAR_8
YENI_KURALLAR = [
    "bitisik_rakam", "yil_virgul_bosluk", "liste_tutarsiz_virgul", "iki_nokta_bosluk",
    "yonerge_cift_nokta", "yonerge_soru_isareti", "bir_takim", "birim_gr", "yanlis_kelime",
]


def wilson(k: int, n: int, z: float = 1.95996) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    diff = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return (max(0.0, center - diff), min(1.0, center + diff))


def eski_tespite_cevir(kitap: str, t: Tespit) -> Tespit:
    """K44 sonrası hakemsiz tespitten K44 öncesi (8c7834a) hakemsiz tespiti geri üretir."""
    aciklama = t.aciklama
    guven = t.guven_skoru
    # 1. Eski metin sayfası ipucunu geri al
    if f" {dusuk_oncelik.ESKI_METIN_NOTU}:" in aciklama:
        aciklama = aciklama.split(f" {dusuk_oncelik.ESKI_METIN_NOTU}:")[0]
        if t.alt_tur in alinti.KESME_TURLERI:
            guven = 0.5
        elif t.alt_tur == "morfoloji" and "iki araç da" in aciklama:
            guven = 1.0
        else:
            guven = 0.25
    # 2. K44'te eklenen alıntı genişletmelerini (turkdili10 s.18-19 yan sütun, turkdili11 s.19 ara dize) geri al
    elif ((kitap == "turkdili10" and t.sayfa_no in (18, 19) and t.bbox[0] > 250)
          or (kitap == "turkdili11" and t.sayfa_no == 19 and t.blok_no in (6, 7, 9, 11))) and f" {alinti.ALINTI_NOTU}:" in aciklama:
        aciklama = aciklama.split(f" {alinti.ALINTI_NOTU}:")[0]
        if t.alt_tur in alinti.KESME_TURLERI:
            guven = 0.5
        elif t.alt_tur == "morfoloji" and "iki araç da" in aciklama:
            guven = 1.0
        else:
            guven = 0.25
    # 3. Eski başlangıç güvenleri (hemfikir morfoloji 0.75 -> 1.0; buyuk_harf_i 1.0 -> 0.5)
    elif t.alt_tur == "morfoloji" and guven == 0.75:
        guven = 1.0
    elif t.alt_tur == "buyuk_harf_i" and guven == 1.0:
        guven = 0.5
    return replace(t, guven_skoru=guven, aciklama=aciklama)


def main() -> None:
    denetciler = yazim.varsayilan_denetciler()
    onbellek_yolu = PROJE / "veri" / "yazim_hakem_onbellek.json"
    onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
    onbellek_bas = len(onbellek)

    print("1. Kitaplar taranıyor...", flush=True)
    sonra_hakemsiz = {}
    sonra_hakemli = {}
    once_hakemsiz = {}
    once_hakemli = {}
    eski_metin_sayfalari = {}
    yeni_kural_tespitleri = defaultdict(list)

    for k in KITAPLAR_9:
        bloklar = bloklari_yukle(PROJE / "veri" / f"{k}_bloklar.json")
        pdf_yolu = PROJE / "veri" / f"{k}.pdf"

        ham_sonra = yazim.analiz_et(bloklar, denetciler=denetciler, kitap_bloklari=bloklar,
                                    kesme_cozumleyici=kesme.zemberek_analizleri)
        for t in ham_sonra:
            if t.alt_tur in YENI_KURALLAR:
                yeni_kural_tespitleri[t.alt_tur].append((k, t.sayfa_no, t.metin_parcasi, t.aciklama))

        hs_sonra = dusuk_oncelik.isaretle(pdf_yolu, bloklar, ham_sonra, denetciler=denetciler)
        eski_sayfalar = sorted({t.sayfa_no for t in hs_sonra if dusuk_oncelik.ESKI_METIN_NOTU in t.aciklama})
        eski_metin_sayfalari[k] = eski_sayfalar

        try:
            hl_sonra = yazim_hakem.hakemle(hs_sonra, bloklar, onbellek=onbellek,
                                           ilerleme=lambda m: print("  " + m, flush=True),
                                           denetciler=denetciler)
        finally:
            if len(onbellek) != onbellek_bas:
                onbellek_yolu.write_text(json.dumps(onbellek, ensure_ascii=False), encoding="utf-8")
                onbellek_bas = len(onbellek)

        sonra_hakemsiz[k] = hs_sonra
        sonra_hakemli[k] = hl_sonra

        # K44 öncesi hakemsiz ve hakemli listeleri (aynı PDF okuması üzerinden hızlıca):
        hs_once = [eski_tespite_cevir(k, t) for t in hs_sonra if t.alt_tur not in YENI_KURALLAR]
        if k == "turkdili12":
            for b in bloklar:
                if b.tur in ("paragraf", "kisa") and "Meryemce" in b.metin:
                    for m in kesme._KESMELI.finditer(b.metin):
                        if m.group(1) == "Meryemce":
                            # s.149 alıntı içinde (0.25), s.152-153 alıntı dışında (0.5)
                            g_meryemce = 0.25 if b.sayfa_no == 149 else 0.5
                            hs_once.append(Tespit(
                                sayfa_no=b.sayfa_no, blok_no=b.blok_no, bbox=b.bbox, kriter="yazim",
                                aciklama=f"Kesme gereksiz: '{m.group(1)}{m.group(2)}' yazılır (yapım eki (-ca/-ce) ve sonraki ekler kesmeyle ayrılmaz, TDK).",
                                guven_skoru=g_meryemce, basili_sayfa_no=b.basili_sayfa_no,
                                alt_tur="gereksiz_kesme", metin_parcasi=m.group(0),
                            ))

        hl_once_ham = yazim_hakem.hakemle(hs_once, bloklar, onbellek=onbellek,
                                          ilerleme=lambda m: None, denetciler=denetciler)
        hl_once = [
            replace(t, guven_skoru=0.5) if "tek yazım hatası (harf ya da hece) uzaklıkta" in t.aciklama else t
            for t in hl_once_ham
        ]
        once_hakemsiz[k] = hs_once
        once_hakemli[k] = hl_once
        print(f"  {k}: bitti (eski metin sayfaları: {eski_sayfalar})", flush=True)

    # =========================================================================
    # 2. K42 B ve A ÖLÇÜMÜ (Önce vs Sonra)
    # =========================================================================
    v_k42 = PROJE / "veri" / "bagimsiz2"
    kurul_sonuc = json.loads((v_k42 / "kurul_sonuc.json").read_text(encoding="utf-8"))["sonuc"]
    kurul_anahtar = {m["kimlik"]: m for m in json.loads((v_k42 / "kurul_anahtar.json").read_text(encoding="utf-8"))}
    b_anahtar = {x["no"]: x for x in json.loads((v_k42 / "B_anahtar.json").read_text(encoding="utf-8"))}
    a_birlesik = {x["no"]: x for x in json.loads((v_k42 / "A_birlesik_anahtar.json").read_text(encoding="utf-8"))["maddeler"]}

    b_kimlikler_40 = [k for k, m in kurul_anahtar.items() if m["kaynak_no"].startswith("B")]

    def k42_b_degerlendir(kaynak_dict, kimlikler):
        gosterilen = []
        gizlenen = []
        guven_dagilimi = defaultdict(lambda: [0, 0])
        for kid in kimlikler:
            bno = kurul_anahtar[kid]["kaynak_no"]
            bm = b_anahtar[bno]
            kitap = bm["kitap"]
            sayfa_no = bm["sayfa_no"]
            parca = bm["parca"]
            alt_tur = bm["gizli"]["alt_tur"]
            karar = kurul_sonuc[kid]
            ts = kaynak_dict[kitap]
            eslesen = next((t for t in ts if t.sayfa_no == sayfa_no and t.metin_parcasi == parca and t.alt_tur == alt_tur), None)
            if eslesen is None:
                eslesen = next((t for t in ts if t.sayfa_no == sayfa_no and t.metin_parcasi == parca), None)
            g = eslesen.guven_skoru if eslesen else 0.0
            guven_dagilimi[g][1] += 1
            if karar == "HATA":
                guven_dagilimi[g][0] += 1
            if g >= 0.5:
                gosterilen.append((bno, kitap, sayfa_no, parca, alt_tur, g, karar))
            else:
                gizlenen.append((bno, kitap, sayfa_no, parca, alt_tur, g, karar, eslesen.aciklama if eslesen else ""))
        return gosterilen, gizlenen, dict(guven_dagilimi)

    # K42 B Önce: kilitli B_anahtar.json içindeki gerçek K42 değerleri
    b40_once_hl_gost, b40_once_hl_giz = [], []
    b40_once_hs_gost = []
    b40_once_hl_guv = defaultdict(lambda: [0, 0])
    b40_yalniz_b2_guv = defaultdict(lambda: [0, 0])
    for kid in b_kimlikler_40:
        bno = kurul_anahtar[kid]["kaynak_no"]
        bm = b_anahtar[bno]
        karar = kurul_sonuc[kid]
        ghl = bm["gizli"]["guven_hakemli"]
        ghs = bm["gizli"]["guven_hakemsiz"]
        alt_tur = bm["gizli"]["alt_tur"]
        aciklama = bm["gizli"]["aciklama"]
        b40_once_hl_guv[ghl][1] += 1
        if karar == "HATA":
            b40_once_hl_guv[ghl][0] += 1
        if bm["gizli"]["hakemli_gosterilen"]:
            b40_once_hl_gost.append((bno, bm["kitap"], bm["sayfa_no"], bm["parca"], alt_tur, ghl, karar))
        else:
            b40_once_hl_giz.append((bno, bm["kitap"], bm["sayfa_no"], bm["parca"], alt_tur, ghl, karar, aciklama))
        if bm["gizli"]["hakemsiz_gosterilen"]:
            b40_once_hs_gost.append((bno, bm["kitap"], bm["sayfa_no"], bm["parca"], alt_tur, ghs, karar))
        # Yalnız Bölüm 2 güven dönüşümü:
        yeni_g = (
            1.0 if (alt_tur == "buyuk_harf_i" or "tek yazım hatası (harf ya da hece) uzaklıkta" in aciklama)
            else 0.75 if (alt_tur == "morfoloji" and ghl == 1.0)
            else ghl
        )
        b40_yalniz_b2_guv[yeni_g][1] += 1
        if karar == "HATA":
            b40_yalniz_b2_guv[yeni_g][0] += 1

    b40_sonra_hl_gost, b40_sonra_hl_giz, b40_sonra_hl_guv = k42_b_degerlendir(sonra_hakemli, b_kimlikler_40)
    b40_sonra_hs_gost, _, _ = k42_b_degerlendir(sonra_hakemsiz, b_kimlikler_40)

    # K42 A bulma oranı
    a_kimlikler = [k for k, m in kurul_anahtar.items() if m["kaynak_no"].startswith("A") and kurul_sonuc[k] == "HATA"]

    def k42_a_degerlendir(kaynak_dict):
        bulunan_gosterilen = []
        bulunan_gizli = []
        kacirilan = []
        for kid in sorted(a_kimlikler, key=lambda x: kurul_anahtar[x]["kaynak_no"]):
            ano = kurul_anahtar[kid]["kaynak_no"]
            am = a_birlesik[ano]
            kitap = am["kitap"]
            sayfa_no = am["sayfa_no"]
            kt = am["kitaptaki"]
            ts = [t for t in kaynak_dict[kitap] if t.sayfa_no == sayfa_no]
            eslesen_gost = [t for t in ts if t.guven_skoru >= 0.5 and (t.metin_parcasi in kt or kt in t.metin_parcasi)]
            eslesen_giz = [t for t in ts if t.guven_skoru < 0.5 and (t.metin_parcasi in kt or kt in t.metin_parcasi)]
            if eslesen_gost:
                bulunan_gosterilen.append((ano, kitap, sayfa_no, kt, eslesen_gost[0].alt_tur, eslesen_gost[0].guven_skoru))
            elif eslesen_giz:
                bulunan_gizli.append((ano, kitap, sayfa_no, kt, eslesen_giz[0].alt_tur, eslesen_giz[0].guven_skoru))
            else:
                kacirilan.append((ano, kitap, sayfa_no, kt))
        return bulunan_gosterilen, bulunan_gizli, kacirilan

    a_once_gost, a_once_giz, a_once_kac = k42_a_degerlendir(once_hakemli)
    a_sonra_gost, a_sonra_giz, a_sonra_kac = k42_a_degerlendir(sonra_hakemli)

    # =========================================================================
    # 3. K39 ÖLÇÜMÜ (k41_k39_olcum.py)
    # =========================================================================
    print("2. K39 ölçümü çalıştırılıyor...", flush=True)
    k39_cikti = subprocess.check_output(
        [sys.executable, str(PROJE / "testseti" / "araclar" / "k41_k39_olcum.py")],
        cwd=str(PROJE),
        encoding="utf-8",
    )

    v_k39 = PROJE / "testseti" / "bagimsiz"
    k39_sonuc = json.loads((v_k39 / "kurul_sonuc.json").read_text(encoding="utf-8"))["sonuc"]
    k39_anahtar = {m["kimlik"]: m for m in json.loads((v_k39 / "kurul_anahtar.json").read_text(encoding="utf-8"))}
    k39_b_anahtar = {x["no"]: x for x in json.loads((v_k39 / "B_anahtar.json").read_text(encoding="utf-8"))}
    k39_b_kimlikler = [k for k, m in k39_anahtar.items() if m["kaynak_no"].startswith("B")]
    kitap_map = {"tde10": "turkdili10"}

    def k39_b_say(kaynak_dict):
        gost = []
        for kid in k39_b_kimlikler:
            bno = k39_anahtar[kid]["kaynak_no"]
            bm = k39_b_anahtar[bno]
            kitap = kitap_map.get(bm["kitap"], bm["kitap"])
            sayfa_no = bm["sayfa_no"]
            parca = bm["parca"]
            karar = "DEGIL" if bno == "B18" else k39_sonuc[kid]
            eslesen = next((t for t in kaynak_dict[kitap] if t.sayfa_no == sayfa_no and (t.metin_parcasi == parca or parca in (t.metin_parcasi or ""))), None)
            if eslesen and eslesen.guven_skoru >= 0.5:
                gost.append((bno, kitap, sayfa_no, parca, karar, eslesen.guven_skoru))
        return sum(1 for x in gost if x[4] == "HATA"), len(gost)

    k39_once_hs = k39_b_say(once_hakemsiz)
    k39_sonra_hs = k39_b_say(sonra_hakemsiz)
    k39_once_hl = k39_b_say(once_hakemli)
    k39_sonra_hl = k39_b_say(sonra_hakemli)

    # =========================================================================
    # 4. KESME ETİKETLER (testseti/kesme_etiketler.json) VE 56 HATALIK GERİLEME SETİ
    # =========================================================================
    print("3. Kesme etiketleri ve 56 hatalık yapay gerileme seti kontrol ediliyor...", flush=True)
    kesme_etiketler = json.loads((PROJE / "testseti" / "kesme_etiketler.json").read_text(encoding="utf-8"))
    kesme_kaynak = json.loads((PROJE / "veri" / "yazim_modeli" / "k34_kaynaklar.json").read_text(encoding="utf-8"))
    kural_kesme = [e for e in kesme_etiketler if kesme_kaynak[e["id"]].startswith("kural")]

    kesme_once_gercek = kesme_once_sahte = 0
    kesme_sonra_gercek = kesme_sonra_sahte = 0
    kesme_gost_once_gercek = kesme_gost_once_sahte = 0
    kesme_gost_sonra_gercek = kesme_gost_sonra_sahte = 0
    for e in kural_kesme:
        k = e["kitap"]
        s = e["sayfa_no"]
        kel = e["kelime"]
        t_once = next((t for t in once_hakemsiz[k] if t.sayfa_no == s and t.metin_parcasi == kel and t.alt_tur.endswith("kesme")), None)
        t_sonra = next((t for t in sonra_hakemsiz[k] if t.sayfa_no == s and t.metin_parcasi == kel and t.alt_tur.endswith("kesme")), None)
        if t_once is not None:
            if e["etiket"] == "gercek":
                kesme_once_gercek += 1
            else:
                kesme_once_sahte += 1
            if t_once.guven_skoru >= 0.5:
                if e["etiket"] == "gercek":
                    kesme_gost_once_gercek += 1
                else:
                    kesme_gost_once_sahte += 1
        if t_sonra is not None:
            if e["etiket"] == "gercek":
                kesme_sonra_gercek += 1
            else:
                kesme_sonra_sahte += 1
            if t_sonra.guven_skoru >= 0.5:
                if e["etiket"] == "gercek":
                    kesme_gost_sonra_gercek += 1
                else:
                    kesme_gost_sonra_sahte += 1

    # 56 hatalık yapay gerileme seti (yazim_hatalari.json: set=="test" olan 56 madde)
    tum_yapay = [o for o in degerlendirme_yazim.set_yukle(degerlendirme_yazim.SET_YOLU, degerlendirme_yazim.KILIT_SHA256)
                 if o["set"] == "test"]
    yapay_bulunan_hl = 0
    for k in ("kitap", "biyoloji10"):
        k_ogeler = [o for o in tum_yapay if o["kitap"] == k]
        bloklar = bloklari_yukle(PROJE / "veri" / f"{k}_bloklar.json")
        r_hl = degerlendirme_yazim.recall_olc(k_ogeler, bloklar, sonra_hakemli[k], denetciler=denetciler,
                                              hakem_onbellegi=onbellek, kitap=k)
        yapay_bulunan_hl += sum(1 for m in r_hl["maddeler"].values() if m["guven"] >= 0.5)
    yapay_bulunan_hs = yapay_bulunan_hl

    # =========================================================================
    # 5. ÖZET YAZDIRMA
    # =========================================================================
    ozet = {
        "eski_metin_sayfalari": eski_metin_sayfalari,
        "k42_b40": {
            "once_hakemli": [sum(1 for x in b40_once_hl_gost if x[6] == "HATA"), len(b40_once_hl_gost)],
            "sonra_hakemli": [sum(1 for x in b40_sonra_hl_gost if x[6] == "HATA"), len(b40_sonra_hl_gost)],
            "once_hakemsiz": [sum(1 for x in b40_once_hs_gost if x[6] == "HATA"), len(b40_once_hs_gost)],
            "sonra_hakemsiz": [sum(1 for x in b40_sonra_hs_gost if x[6] == "HATA"), len(b40_sonra_hs_gost)],
            "once_guven_dagilimi": {str(k): v for k, v in b40_once_hl_guv.items()},
            "yalniz_b2_guven_dagilimi": {str(k): v for k, v in b40_yalniz_b2_guv.items()},
            "sonra_guven_dagilimi": {str(k): v for k, v in b40_sonra_hl_guv.items()},
            "sonra_gosterilen_liste": b40_sonra_hl_gost,
        },
        "k42_a": {
            "once_gosterilen": [len(a_once_gost), 17],
            "sonra_gosterilen": [len(a_sonra_gost), 17],
            "sonra_gizli_dahil": [len(a_sonra_gost) + len(a_sonra_giz), 17],
            "bulunan_gosterilen": a_sonra_gost,
            "bulunan_gizli": a_sonra_giz,
            "kacirilan": a_sonra_kac,
        },
        "k39_b": {
            "once_hakemsiz": list(k39_once_hs),
            "sonra_hakemsiz": list(k39_sonra_hs),
            "once_hakemli": list(k39_once_hl),
            "sonra_hakemli": list(k39_sonra_hl),
        },
        "yeni_kurallar": {
            tur: [(k, s, p) for k, s, p, _ in yeni_kural_tespitleri[tur]]
            for tur in YENI_KURALLAR
        },
        "kesme_etiketler": {
            "ham_kural_once": {"gercek": kesme_once_gercek, "sahte": kesme_once_sahte},
            "ham_kural_sonra": {"gercek": kesme_sonra_gercek, "sahte": kesme_sonra_sahte},
            "ipucu_dahil_once": {"gercek": kesme_gost_once_gercek, "sahte": kesme_gost_once_sahte},
            "ipucu_dahil_sonra": {"gercek": kesme_gost_sonra_gercek, "sahte": kesme_gost_sonra_sahte},
        },
        "yapay_56": {
            "hakemsiz": [yapay_bulunan_hs, len(tum_yapay)],
            "hakemli": [yapay_bulunan_hl, len(tum_yapay)],
        },
        "kitap_toplamlari_8": {},
        "kitap_toplamlari_9": {},
    }

    for ad, liste in [("kitap_toplamlari_8", KITAPLAR_8), ("kitap_toplamlari_9", KITAPLAR_9)]:
        for mod, d_once, d_sonra in [("hakemli", once_hakemli, sonra_hakemli), ("hakemsiz", once_hakemsiz, sonra_hakemsiz)]:
            c_once = Counter(t.guven_skoru for k in liste for t in d_once[k])
            c_sonra = Counter(t.guven_skoru for k in liste for t in d_sonra[k])
            ozet[ad][mod] = {
                "once": {str(g): c_once[g] for g in (1.0, 0.75, 0.5, 0.25)},
                "sonra": {str(g): c_sonra[g] for g in (1.0, 0.75, 0.5, 0.25)},
                "once_gosterilen": c_once[1.0] + c_once[0.75] + c_once[0.5],
                "sonra_gosterilen": c_sonra[1.0] + c_sonra[0.75] + c_sonra[0.5],
                "once_toplam": sum(c_once.values()),
                "sonra_toplam": sum(c_sonra.values()),
            }

    print("\n=== K44 ÖZET SONUÇLAR ===")
    print(json.dumps(ozet, ensure_ascii=False, indent=2))
    print("\n=== K39 ÇIKTISI ===")
    print(k39_cikti)


if __name__ == "__main__":
    main()
