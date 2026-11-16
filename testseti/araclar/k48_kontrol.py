"""K48 geliştirme kontrolü (yalnız bilgi): ürün hattı (sayfa okuma açık) K42 ve K45 A sayfalarında 44 gerçek hatadan kaçını gösteriyor.

Çalıştırma: D:\\derskitabı\\.venv\\Scripts\\python.exe testseti/araclar/k48_kontrol.py   (Ollama açık olmalı)
Çıktı: testseti/k48_gelistirme.md, veri/k48/kontrol.json
"""
import json
import time
from collections import Counter

from k47_ortak import (KITAP_TAM_AD, PROJE, a_verisini_yukle, eslesir_mi, sayfalari_yukle)

from derskitabi.kayit import bloklari_yukle
from derskitabi.kriterler import dusuk_oncelik, sayfa_okuma, yazim
from derskitabi.kriterler.yazim_hakem import hakemle

CIKTI = PROJE / "veri" / "k48"
CIKTI.mkdir(parents=True, exist_ok=True)


def bulunan(gercek: list[dict], tespitler_sayfa: dict[str, list]) -> set[str]:
    return {g["id"] for g in gercek
            if any(t.guven_skoru >= 0.5 and t.metin_parcasi and eslesir_mi(t.metin_parcasi, g["kitaptaki"])
                   for t in tespitler_sayfa.get(g["sayfa_id"], []))}


def main() -> None:
    sayfalar = sayfalari_yukle()
    gercek, _ = a_verisini_yukle()
    hakem_onbellek_yolu = PROJE / "veri" / "yazim_hakem_onbellek.json"
    hakem_onbellek = json.loads(hakem_onbellek_yolu.read_text(encoding="utf-8")) if hakem_onbellek_yolu.exists() else {}
    okuma_onbellek_yolu = PROJE / "veri" / sayfa_okuma.ONBELLEK_ADI
    okuma_onbellek = sayfa_okuma.onbellek_yukle(okuma_onbellek_yolu)

    once, sonra = {s["sayfa_id"]: [] for s in sayfalar}, {s["sayfa_id"]: [] for s in sayfalar}
    sayac = Counter()
    sureler = {}
    mesajlar = []
    for kitap in dict.fromkeys(s["kitap"] for s in sayfalar):
        k_sayfalar = [s for s in sayfalar if s["kitap"] == kitap]
        no_id = {s["sayfa_no"]: s["sayfa_id"] for s in k_sayfalar}
        bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        pdf = PROJE / "veri" / f"{kitap}.pdf"
        hakemsiz = dusuk_oncelik.isaretle(pdf, bloklar, yazim.analiz_et(bloklar))
        secili = [t for t in hakemsiz if t.sayfa_no in no_id]
        hakemli = hakemle(secili, bloklar, onbellek=hakem_onbellek)
        hakem_onbellek_yolu.write_text(json.dumps(hakem_onbellek, ensure_ascii=False), encoding="utf-8")
        for t in hakemli:
            once[no_id[t.sayfa_no]].append(t)

        t0 = time.perf_counter()
        sayfa_nolari = set(no_id)
        try:
            son, k_sayac = sayfa_okuma.uygula(
                hakemli, bloklar, sayfalar=sayfa_nolari,
                alintilar=sayfa_okuma.alintilari_bul(pdf, bloklar, sayfa_nolari), onbellek=okuma_onbellek,
                ilerleme=lambda m: (mesajlar.append(m), print(m, flush=True)), kitap_adi=KITAP_TAM_AD[kitap])
        finally:
            sayfa_okuma.onbellek_kaydet(okuma_onbellek, okuma_onbellek_yolu)
        sureler[kitap] = round(time.perf_counter() - t0, 1)
        sayac.update(k_sayac)
        for t in son:
            if t.sayfa_no in no_id:
                sonra[no_id[t.sayfa_no]].append(t)

    once_id, sonra_id = bulunan(gercek, once), bulunan(gercek, sonra)
    so_tespit = {sid: [t for t in lst if t.alt_tur == sayfa_okuma.ALT_TUR] for sid, lst in sonra.items()}
    gosterilen = {sid: [t for t in lst if t.guven_skoru >= 0.5] for sid, lst in so_tespit.items()}
    toplam_gos = sum(map(len, gosterilen.values()))
    so_bulunan = {g["id"] for g in gercek if any(
        eslesir_mi(t.metin_parcasi, g["kitaptaki"]) for t in gosterilen.get(g["sayfa_id"], []))}
    eslesmeyen = sum(1 for sid, lst in gosterilen.items() for t in lst
                     if not any(g["sayfa_id"] == sid and eslesir_mi(t.metin_parcasi, g["kitaptaki"]) for g in gercek))
    toplam_sure = round(sum(sureler.values()), 1)
    sinif = {s: [sum(1 for g in gercek if g["sinif"] == s and g["id"] in kume), sum(1 for g in gercek if g["sinif"] == s)]
             for s in ("noktalama", "kelime", "diger") for kume in (sonra_id,)}

    veri = {"once": sorted(once_id), "sonra": sorted(sonra_id), "ek": sorted(sonra_id - once_id),
            "sayfa_okuma_ile_eslesen": sorted(so_bulunan), "tespit_gosterilen": toplam_gos,
            "tespit_toplam": sum(map(len, so_tespit.values())), "eslesmeyen_gosterilen": eslesmeyen,
            "sayac": dict(sayac), "sureler_sn": sureler, "toplam_sure_sn": toplam_sure}
    (CIKTI / "kontrol.json").write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")

    satir = []
    satir += ["# K48 geliştirme kontrolü: sayfa okuma ürün hattında", "",
              "**Geliştirme verisi; süzgeçler bu sayfalara bakılarak yazıldı. Gerçek etki K49'da yeni kitapta ölçülecek.**", "",
              f"Sayfalar: K42 ve K45 A sayfaları (60), kurulun HATA dediği 44 gerçek hata. Hat: yazım denetimi + kitap ipuçları + "
              f"yazım hakemi + sayfa okuma (`{sayfa_okuma.MODEL}`, istem sürümü `{sayfa_okuma.ISTEM_SURUMU}`).", "",
              "## Sonuç", "", "| Ölçü | Değer |", "|---|---|",
              f"| Sayfa okuma kapalıyken gösterilen (güven ≥ 0,5) tespitlerle bulunan | {len(once_id)} / 44 |",
              f"| Sayfa okuma açıkken bulunan | **{len(sonra_id)} / 44** |",
              f"| Sayfa okumanın eklediği (önceden bulunmayan) | {len(sonra_id - once_id)} |",
              f"| Sayfa okuma tespitiyle eşleşen gerçek hata (toplam) | {len(so_bulunan)} |",
              f"| Sayfa okuma tespiti (güven ≥ 0,5) | {toplam_gos} (sayfa başına {toplam_gos / 60:.2f}) |",
              f"| Sayfa okuma tespiti, gerçek hatayla eşleşmeyen | {eslesmeyen} (sayfa başına {eslesmeyen / 60:.2f}) |",
              f"| Alıntı içinde güveni 0,25'e inen sayfa okuma tespiti | {sayac['alinti_dusuk']} |",
              f"| Modelden gelen aday | {sayac['model_adayi']} |",
              f"| Okunan / atlanan sayfa | {sayac['okunan_sayfa']} / {sayac['atlanan_sayfa']} |",
              f"| Önbellekten gelen sayfa | {sayac['onbellekten']} |",
              f"| Süre (yalnız sayfa okuma adımı, önbellek hariç/dahil) | {toplam_sure} sn ({toplam_sure / 60:.2f} sn/sayfa; "
              f"300 sayfalık kitap için ~{toplam_sure / 60 * 300 / 60:.0f} dk) |", "",
              "## Süzgeçlerin attığı adaylar (sebebe göre)", "", "| Sebep | Aday |", "|---|---|"]
    for k, ad in sayfa_okuma.SURZGEC_ADLARI.items():
        satir.append(f"| {ad} | {sayac[k]} |")
    satir += ["", "## Sınıfa göre (sayfa okuma açık)", "", "| Sınıf | Bulunan |", "|---|---|"]
    for s in ("noktalama", "kelime", "diger"):
        satir.append(f"| {s} | {sinif[s][0]} / {sinif[s][1]} |")
    satir += ["", "## Sayfa okumanın eklediği gerçek hatalar", ""]
    for g in sorted(gercek, key=lambda g: g["id"]):
        if g["id"] in sonra_id - once_id:
            satir.append(f"- `{g['id']}`: `{g['kitaptaki']}` → `{g['onerilen']}`")
    satir += ["", "## Hâlâ bulunamayanlar", ""]
    satir.append(", ".join(f"`{g['id']}`" for g in sorted(gercek, key=lambda g: g["id"]) if g["id"] not in sonra_id))
    satir += ["", "## Kitap başına süre (sayfa okuma)", "", "| Kitap | Süre |", "|---|---|"]
    for k, sn in sureler.items():
        satir.append(f"| {KITAP_TAM_AD[k]} | {sn} sn |")
    satir += ["", "> Not: süre önbellekten gelen sayfaları içermez; önbellek boşken yaklaşık 15 sn/sayfa (K47)."]
    (PROJE / "testseti" / "k48_gelistirme.md").write_text("\n".join(satir) + "\n", encoding="utf-8")
    print(f"Önce {len(once_id)}/44, sonra {len(sonra_id)}/44; sayfa okuma tespiti {toplam_gos} ({toplam_gos / 60:.2f}/sayfa); "
          f"süre {toplam_sure} sn")


if __name__ == "__main__":
    main()
