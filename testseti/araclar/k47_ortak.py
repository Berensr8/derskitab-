"""K47 araç taraması: ortak veri yükleme, hata sınıflama, eşleşme kuralı ve mevcut sistem (HEAD) değerlendirmesi."""
import json
import random
import re
import sys
from pathlib import Path

import pymupdf

PROJE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE))
sys.stdout.reconfigure(encoding="utf-8")

BEKLENEN_PYMUPDF = "1.28.2"
if pymupdf.__version__ != BEKLENEN_PYMUPDF:
    sys.exit(f"DUR: PyMuPDF {pymupdf.__version__}; beklenen {BEKLENEN_PYMUPDF}. .venv Python'u kullanın.")

from derskitabi.kayit import bloklari_yukle
from derskitabi.kriterler import dusuk_oncelik, yazim
from derskitabi.kriterler.yazim import tr_kucuk
from derskitabi.kriterler.yazim_hakem import hakemle

TOHUM = 20261117
CIKTI_KLASOR = PROJE / "veri" / "k47"
CIKTI_KLASOR.mkdir(parents=True, exist_ok=True)

KITAP_TAM_AD = {
    "biyoloji9": "Biyoloji 9",
    "biyoloji11": "Biyoloji 11",
    "turkdili10": "Türk Dili ve Edebiyatı 10",
    "biyoloji12": "Biyoloji 12",
    "inkilap12": "T.C. İnkılâp Tarihi ve Atatürkçülük 12",
}


def norm(metin: str) -> str:
    """Boşluk ve büyük/küçük harf farkını kaldırır; kıvrık kesme/tırnakları düzleştirir (K43 ile aynı)."""
    m = tr_kucuk(metin or "")
    m = m.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", "", m)


def eslesir_mi(aday_kitaptaki: str, hedef_kitaptaki: str) -> bool:
    """Ön kayıt eşleşme kuralı: biri diğerini içeriyorsa (boşluk, harf büyüklüğü, kıvrık/düz kesme hariç) True."""
    m = norm(aday_kitaptaki)
    h = norm(hedef_kitaptaki)
    if len(m) < 2 or len(h) < 2:
        return False
    return (m in h) or (h in m)


def _norm_nokt(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\s*[,;:?!.]+\s*", " ", s.strip())).strip()


def hata_sinifi(kitaptaki: str, onerilen: str) -> str:
    """Mekanik hata sınıfı (k47_on_kayit.md): noktalama, kelime, diger."""
    k = kitaptaki.strip()
    o = onerilen.strip()
    if _norm_nokt(k) == _norm_nokt(o) and k != o:
        return "noktalama"
    if len(k.split()) == 1 and len(o.split()) == 1 and any(c.isalpha() for c in k) and any(c.isalpha() for c in o):
        return "kelime"
    return "diger"


def sayfalari_yukle() -> list[dict]:
    """K42 (30) ve K45 (30) A sayfalarını bloklarıyla birlikte döndürür (toplam 60 sayfa)."""
    kitap_bloklari = {}
    sayfalar = []
    for on_ek, p_rel in (("K42", "bagimsiz_degerlendirme2"), ("K45", "bagimsiz_degerlendirme3")):
        liste = json.loads((PROJE / p_rel / "A_sayfa_listesi.json").read_text(encoding="utf-8"))
        for x in liste:
            k = x["kitap"]
            if k not in kitap_bloklari:
                kitap_bloklari[k] = bloklari_yukle(PROJE / "veri" / f"{k}_bloklar.json")
            s_no = x["sayfa_no"]
            s_bloklar = [b for b in kitap_bloklari[k] if b.sayfa_no == s_no]
            kod = x["kod"]
            sayfa_id = f"{on_ek}_{kod}"
            sayfalar.append({
                "sayfa_id": sayfa_id,
                "set": on_ek,
                "kod": kod,
                "kitap": k,
                "sayfa_no": s_no,
                "baslik": f"{KITAP_TAM_AD[k]}, PDF s.{s_no}",
                "bloklar": s_bloklar,
            })
    assert len(sayfalar) == 60, f"60 sayfa bekleniyordu, {len(sayfalar)} bulundu"
    return sayfalar


def a_verisini_yukle() -> tuple[list[dict], list[dict]]:
    """44 gerçek hatayı ve 106 kurul reddi (DEGIL/BELIRSIZ) adayını döndürür."""
    gercek_hatalar = []
    kurul_degil = []
    for on_ek, v_rel in (("K42", "veri/bagimsiz2"), ("K45", "veri/bagimsiz3")):
        v = PROJE / v_rel
        a_maddeler = {
            x["no"]: x
            for x in json.loads((v / "A_birlesik_anahtar.json").read_text(encoding="utf-8"))["maddeler"]
        }
        kurul_anahtar = {
            m["kaynak_no"]: m["kimlik"]
            for m in json.loads((v / "kurul_anahtar.json").read_text(encoding="utf-8"))
            if m["kaynak_no"].startswith("A")
        }
        kurul_sonuc = json.loads((v / "kurul_sonuc.json").read_text(encoding="utf-8"))["sonuc"]
        for no, m in sorted(a_maddeler.items()):
            kimlik = kurul_anahtar[no]
            etiket = kurul_sonuc[kimlik]
            sinif = hata_sinifi(m["kitaptaki"], m["onerilen"])
            kayit = {
                **m,
                "set": on_ek,
                "id": f"{on_ek}_{no}",
                "sayfa_id": f"{on_ek}_{m['sayfa']}",
                "kimlik": kimlik,
                "etiket": etiket,
                "sinif": sinif,
            }
            if etiket == "HATA":
                gercek_hatalar.append(kayit)
            else:
                kurul_degil.append(kayit)
    assert len(gercek_hatalar) == 44, f"44 gerçek hata bekleniyordu, {len(gercek_hatalar)} bulundu"
    return gercek_hatalar, kurul_degil


def mevcut_sistem_sonuclari() -> dict:
    """Bugünkü ürünün (HEAD, K46 dahil) 60 A sayfasında gösterdiği (güven >= 0,5) tespitler ve yakaladığı hatalar."""
    cache_yolu = CIKTI_KLASOR / "mevcut_sistem.json"
    if cache_yolu.exists():
        return json.loads(cache_yolu.read_text(encoding="utf-8"))

    sayfalar = sayfalari_yukle()
    gercek_hatalar, kurul_degil = a_verisini_yukle()
    onbellek_yolu = PROJE / "veri" / "yazim_hakem_onbellek.json"
    onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}

    kitap_sayfa_map = {}
    for s in sayfalar:
        kitap_sayfa_map.setdefault(s["kitap"], {})[s["sayfa_no"]] = s["sayfa_id"]

    sayfa_adaylari = {s["sayfa_id"]: [] for s in sayfalar}
    for kitap, s_map in kitap_sayfa_map.items():
        bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        pdf_yolu = PROJE / "veri" / f"{kitap}.pdf"
        hakemsiz = dusuk_oncelik.isaretle(pdf_yolu, bloklar, yazim.analiz_et(bloklar))
        secili = [t for t in hakemsiz if t.sayfa_no in s_map]
        hakemli = hakemle(secili, bloklar, onbellek=onbellek)
        onbellek_yolu.write_text(json.dumps(onbellek, ensure_ascii=False), encoding="utf-8")
        for t in hakemli:
            if t.guven_skoru >= 0.5 and t.metin_parcasi:
                sid = s_map[t.sayfa_no]
                sayfa_adaylari[sid].append({
                    "kitaptaki": t.metin_parcasi,
                    "onerilen": "",
                    "gerekce": f"{t.alt_tur} (g={t.guven_skoru}): {t.aciklama}",
                    "alt_tur": t.alt_tur,
                    "guven_skoru": t.guven_skoru,
                })

    bulunan_id = []
    for gh in gercek_hatalar:
        adaylar = sayfa_adaylari.get(gh["sayfa_id"], [])
        if any(eslesir_mi(a["kitaptaki"], gh["kitaptaki"]) for a in adaylar):
            bulunan_id.append(gh["id"])

    veri = {
        "bulunan_id": bulunan_id,
        "bulunan_sayisi": len(bulunan_id),
        "sayfa_adaylari": sayfa_adaylari,
    }
    cache_yolu.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    return veri


def arac_degerlendir(
    sayfa_adaylari: dict[str, list[dict]],
    gercek_hatalar: list[dict],
    kurul_degil: list[dict],
    mevcut_bulunan_id: set[str],
    tohum: int = TOHUM,
) -> dict:
    """Bir aracın 60 sayfadaki adaylarını 44 gerçek hata ve 106 kurul reddiyle karşılaştırır."""
    bulunan = []
    kacan = []
    for gh in gercek_hatalar:
        adaylar = sayfa_adaylari.get(gh["sayfa_id"], [])
        es = [a for a in adaylar if eslesir_mi(a.get("kitaptaki", ""), gh["kitaptaki"])]
        if es:
            bulunan.append({"hata": gh, "eslesen_adaylar": es})
        else:
            kacan.append(gh)

    tum_adaylar = []
    gercek_eslesen_sayisi = 0
    degil_eslesen = []
    tamamen_yeni = []

    for sayfa_id, adaylar in sorted(sayfa_adaylari.items()):
        s_gercek = [g for g in gercek_hatalar if g["sayfa_id"] == sayfa_id]
        s_degil = [d for d in kurul_degil if d["sayfa_id"] == sayfa_id]
        for a in adaylar:
            k_metin = a.get("kitaptaki", "")
            kayit_a = {"sayfa_id": sayfa_id, **a}
            tum_adaylar.append(kayit_a)
            es_g = [g for g in s_gercek if eslesir_mi(k_metin, g["kitaptaki"])]
            if es_g:
                gercek_eslesen_sayisi += 1
                continue
            es_d = [d for d in s_degil if eslesir_mi(k_metin, d["kitaptaki"])]
            if es_d:
                degil_eslesen.append({**kayit_a, "kurul_degil_id": [d["id"] for d in es_d]})
            else:
                tamamen_yeni.append(kayit_a)

    eslesmeyen = degil_eslesen + tamamen_yeni
    rng = random.Random(tohum)
    ornek_10 = rng.sample(eslesmeyen, min(10, len(eslesmeyen)))

    bulunan_id = {b["hata"]["id"] for b in bulunan}
    ek_bulunan_id = sorted(bulunan_id - mevcut_bulunan_id)

    sinif_bulunan = {"noktalama": 0, "kelime": 0, "diger": 0}
    sinif_toplam = {"noktalama": 0, "kelime": 0, "diger": 0}
    for gh in gercek_hatalar:
        sinif_toplam[gh["sinif"]] += 1
        if gh["id"] in bulunan_id:
            sinif_bulunan[gh["sinif"]] += 1

    return {
        "bulunan_sayisi": len(bulunan),
        "toplam_gercek_hata": len(gercek_hatalar),
        "sinif_bulunan": sinif_bulunan,
        "sinif_toplam": sinif_toplam,
        "mevcut_sistemin_bulmadigi_ama_aracin_buldugu": len(ek_bulunan_id),
        "ek_bulunan_id": ek_bulunan_id,
        "bulunan_id": sorted(bulunan_id),
        "toplam_isaret": len(tum_adaylar),
        "sayfa_basi_isaret": round(len(tum_adaylar) / 60, 2),
        "gercek_hatayla_eslesen_isaret": gercek_eslesen_sayisi,
        "eslesmeyen_isaret_toplam": len(eslesmeyen),
        "sayfa_basi_eslesmeyen_isaret": round(len(eslesmeyen) / 60, 2),
        "kurul_reddi_ile_eslesen": len(degil_eslesen),
        "tamamen_yeni_isaret": len(tamamen_yeni),
        "bulunan_hatalar": bulunan,
        "kacan_hatalar": kacan,
        "ornek_10_eslesmeyen": ornek_10,
    }


if __name__ == "__main__":
    gercek, degil = a_verisini_yukle()
    print("44 gerçek hata sınıf dağılımı:", {s: sum(g["sinif"] == s for g in gercek) for s in ("noktalama", "kelime", "diger")})
    mevcut = mevcut_sistem_sonuclari()
    print(f"Mevcut sistem (HEAD) yakalanan: {mevcut['bulunan_sayisi']} / 44 -> {mevcut['bulunan_id']}")
