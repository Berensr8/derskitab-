"""K47 Araç 2: hunspell-tr (spylls) taraması — (a) yanlış alarm süzgeci, (b) bulucu, (c) öneri kalitesi."""
import itertools
import json
import time

from spylls.hunspell import Dictionary

from k47_ortak import CIKTI_KLASOR, PROJE, a_verisini_yukle, arac_degerlendir, mevcut_sistem_sonuclari, sayfalari_yukle

from derskitabi.kayit import bloklari_yukle
from derskitabi.kriterler import dusuk_oncelik
from derskitabi.kriterler.yazim import (
    BLOK_MIN_KELIME,
    DUSMUS_HARF_ESIGI,
    OKUMA_SORUNU_ORANI,
    TERIM_TEKRAR_ESIGI,
    _KELIME,
    _WEB,
    _aralikli_mi,
    _atlanma_sebebi,
    _gecerli,
    _harf_dusmus_mu,
    _tespit,
    birlesik_paragraf,
    kitap_kelime_sayilari,
    satir_gruplari,
    satira_bagla,
    tr_kucuk,
    varsayilan_denetciler,
)

SOZLUK_YOLU = PROJE / "modeller" / "hunspell-tr" / "tr_TR"


def hunspell_gecerli_mi(sozluk, kelime: str) -> bool:
    """Kelimeyi ve Türkçe küçük harfli biçimlerini (_gecerli ile aynı adaylarla) hunspell ile sınar."""
    adaylar = [kelime, tr_kucuk(kelime)]
    if "I" in kelime:
        adaylar.append(tr_kucuk(kelime.replace("I", "İ")))
    for aday in dict.fromkeys(adaylar):
        if aday and sozluk.lookup(aday):
            return True
    return False


def bolum_a_suzgec(sozluk) -> dict:
    """(a) K42 ve K45 B listelerindeki kurul etiketli morfoloji tespitlerinde yanlış alarm süzgeci."""
    kayitlar_hakemli = []
    kayitlar_birlesik = []

    for on_ek, v_rel in (("K42", "veri/bagimsiz2"), ("K45", "veri/bagimsiz3")):
        v = PROJE / v_rel
        b_map = {x["no"]: x for x in json.loads((v / "B_anahtar.json").read_text(encoding="utf-8"))}
        k_map = {
            m["kaynak_no"]: m["kimlik"]
            for m in json.loads((v / "kurul_anahtar.json").read_text(encoding="utf-8"))
            if m["kaynak_no"].startswith("B")
        }
        sonuc = json.loads((v / "kurul_sonuc.json").read_text(encoding="utf-8"))["sonuc"]

        for no, x in sorted(b_map.items()):
            if x.get("katman_farki") or no not in k_map:
                continue
            g = x["gizli"]
            if g["alt_tur"] != "morfoloji":
                continue
            kimlik = k_map[no]
            etiket = sonuc[kimlik]
            kelime = x["parca"].strip()
            h_gecerli = hunspell_gecerli_mi(sozluk, kelime)
            veri = {
                "id": f"{on_ek}_{no}",
                "kimlik": kimlik,
                "kitap": x["kitap"],
                "sayfa_no": x["sayfa_no"],
                "kelime": kelime,
                "etiket": etiket,
                "hunspell_gecerli": h_gecerli,
                "hakemli_gosterilen": bool(g["hakemli_gosterilen"]),
            }
            kayitlar_birlesik.append(veri)
            if g["hakemli_gosterilen"]:
                kayitlar_hakemli.append(veri)

    def ozetle(liste: list[dict]) -> dict:
        hata_top = [r for r in liste if r["etiket"] == "HATA"]
        degil_top = [r for r in liste if r["etiket"] == "DEGIL"]
        hata_kayip = [r for r in hata_top if r["hunspell_gecerli"]]
        degil_inen = [r for r in degil_top if r["hunspell_gecerli"]]
        degil_oran = len(degil_inen) / len(degil_top) if degil_top else 0.0
        gecti = (len(hata_kayip) <= 1) and (degil_oran >= 0.30)
        return {
            "toplam_morfoloji": len(liste),
            "hata_toplam": len(hata_top),
            "hata_kayip_sayisi": len(hata_kayip),
            "hata_kayiplar": hata_kayip,
            "degil_toplam": len(degil_top),
            "degil_inen_sayisi": len(degil_inen),
            "degil_inen_oran": round(degil_oran, 4),
            "degil_inenler": degil_inen,
            "karar": "Geçti" if gecti else "Kapatıldı",
        }

    return {
        "hakemli_gosterilen": ozetle(kayitlar_hakemli),
        "birlesik_b": ozetle(kayitlar_birlesik),
    }


def _hunspell_kitaba_ozel_terimler(adaylar: set[str], kitap_kelimeleri, sozluk) -> set[str]:
    """Kitapta >= TERIM_TEKRAR_ESIGI kez geçen ve hunspell'in tanımadığı terimler."""
    terimler = set()
    for aday in adaylar:
        kok = next(
            (
                aday[:i]
                for i in range(len(aday), 4, -1)
                if kitap_kelimeleri[aday[:i]] >= TERIM_TEKRAR_ESIGI
                and (i == len(aday) or not hunspell_gecerli_mi(sozluk, aday[:i]))
            ),
            None,
        )
        if kok:
            terimler.add(aday)
    return terimler


def bolum_b_bulucu(sozluk, sayfalar: list[dict], gercek_hatalar: list[dict], kurul_degil: list[dict], mevcut_id: set[str]) -> dict:
    """(b) 60 sayfada Starlang ve Zemberek'in geçerli saydığı ama hunspell'in tanımadığı kelimeler."""
    denetciler = varsayilan_denetciler()
    starlang, zemberek = denetciler

    kitap_blok_haritasi = {}
    kitap_kelime_sayaci = {}
    for kitap in {s["kitap"] for s in sayfalar}:
        tum_bl = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        kitap_blok_haritasi[kitap] = tum_bl
        kitap_kelime_sayaci[kitap] = kitap_kelime_sayilari(tum_bl)

    t0 = time.perf_counter()
    sayfa_adaylari_filtreli: dict[str, list[dict]] = {s["sayfa_id"]: [] for s in sayfalar}
    sayfa_adaylari_ham: dict[str, list[dict]] = {s["sayfa_id"]: [] for s in sayfalar}

    # Kitap bazında tespitleri toplayıp ürünün dusuk_oncelik süzgecinden geçirelim
    kitap_sayfalari: dict[str, list[dict]] = {}
    for s in sayfalar:
        kitap_sayfalari.setdefault(s["kitap"], []).append(s)

    for kitap, k_sayfalar in kitap_sayfalari.items():
        tum_bl = kitap_blok_haritasi[kitap]
        k_sayilari = kitap_kelime_sayaci[kitap]
        kitap_tespitleri = []
        sayfa_no_to_id = {s["sayfa_no"]: s["sayfa_id"] for s in k_sayfalar}

        for s in k_sayfalar:
            sid = s["sayfa_id"]
            gorulen_ham = set()
            for grup in satir_gruplari(s["bloklar"]):
                b = grup[0] if len(grup) == 1 else birlesik_paragraf(grup, denetciler)
                if b.tur not in ("paragraf", "kisa"):
                    continue
                metin = _WEB.sub(lambda w: " " * len(w.group(0)), b.metin)
                if _aralikli_mi(metin):
                    continue
                eslesmeler = list(_KELIME.finditer(metin))
                sonuclar = [(_gecerli(starlang, m.group(0)), _gecerli(zemberek, m.group(0))) for m in eslesmeler]
                uzunlar = [(st, zb) for m, (st, zb) in zip(eslesmeler, sonuclar) if len(m.group(0)) >= 4]
                ikisi_gecersiz = sum(1 for st, zb in uzunlar if not st and not zb)
                if len(uzunlar) >= BLOK_MIN_KELIME and ikisi_gecersiz / len(uzunlar) > OKUMA_SORUNU_ORANI:
                    continue
                dusmus = sum(
                    1
                    for m, (st, zb) in zip(eslesmeler, sonuclar)
                    if not st and not zb and len(m.group(0)) >= 4 and m.group(0).islower() and _harf_dusmus_mu(m.group(0), denetciler)
                )
                if dusmus >= DUSMUS_HARF_ESIGI:
                    continue

                blok_tespitleri = []
                for i, (m, (st_gecerli, zb_gecerli)) in enumerate(zip(eslesmeler, sonuclar)):
                    kelime = m.group(0)
                    # Yalnız Starlang ve Zemberek'in İKİSİNİN DE geçerli saydığı kelimeler
                    if not (st_gecerli and zb_gecerli):
                        continue
                    # Mevcut atlama kuralları (kısaltma, özel isim, çok kısa, sayı/sembol, bölünmüş kelime vb.)
                    sebep = _atlanma_sebebi(metin, m, ilk=(i == 0), son=(i == len(eslesmeler) - 1))
                    if sebep:
                        continue
                    # Hunspell tanımıyorsa
                    if hunspell_gecerli_mi(sozluk, kelime):
                        continue

                    k_kucuk = tr_kucuk(kelime)
                    if k_kucuk not in gorulen_ham:
                        gorulen_ham.add(k_kucuk)
                        sayfa_adaylari_ham[sid].append({
                            "kitaptaki": kelime,
                            "onerilen": "",
                            "gerekce": "Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı",
                        })
                    blok_tespitleri.append(
                        _tespit(b, "morfoloji", 0.75, kelime, f"'{kelime}' hunspell-tr tarafından tanınmadı.")
                    )
                kitap_tespitleri += satira_bagla(blok_tespitleri, grup, b.metin)

        # Kitaba özel tekrar eden terimleri çıkar (TERIM_TEKRAR_ESIGI = 3)
        terimler = _hunspell_kitaba_ozel_terimler({tr_kucuk(t.metin_parcasi) for t in kitap_tespitleri}, k_sayilari, sozluk)
        kalan = [t for t in kitap_tespitleri if tr_kucuk(t.metin_parcasi) not in terimler]

        # Alıntı, terim (sözlük, tanım, italik) ve PDF parçası süzgeci (dusuk_oncelik.isaretle)
        pdf_yolu = PROJE / "veri" / f"{kitap}.pdf"
        if pdf_yolu.exists() and kalan:
            kalan = dusuk_oncelik.isaretle(pdf_yolu, tum_bl, kalan)

        gorulen_flt: dict[str, set[str]] = {s["sayfa_id"]: set() for s in k_sayfalar}
        for t in kalan:
            if t.guven_skoru < 0.5:
                continue
            sid = sayfa_no_to_id.get(t.sayfa_no)
            if not sid:
                continue
            k_kucuk = tr_kucuk(t.metin_parcasi)
            if k_kucuk not in gorulen_flt[sid]:
                gorulen_flt[sid].add(k_kucuk)
                sayfa_adaylari_filtreli[sid].append({
                    "kitaptaki": t.metin_parcasi,
                    "onerilen": "",
                    "gerekce": "Starlang+Zemberek geçerli saydı, hunspell-tr tanımadı",
                })

    sure_sn = round(time.perf_counter() - t0, 2)
    deg_flt = arac_degerlendir(sayfa_adaylari_filtreli, gercek_hatalar, kurul_degil, mevcut_id)
    deg_ham = arac_degerlendir(sayfa_adaylari_ham, gercek_hatalar, kurul_degil, mevcut_id)

    for deg in (deg_flt, deg_ham):
        kel_bul = deg["sinif_bulunan"]["kelime"]
        gecti = (kel_bul >= 3) and (deg["sayfa_basi_eslesmeyen_isaret"] < 1.0)
        deg["karar"] = "Geçti" if gecti else "Kapatıldı"

    return {
        "sure_sn": sure_sn,
        "sayfa_basi_sure_sn": round(sure_sn / 60, 3),
        "ana_sonuc_filtreli": deg_flt,
        "ham_sonuc_tum_bloklar": deg_ham,
    }


def bolum_c_oneriler(sozluk, gercek_hatalar: list[dict]) -> dict:
    """Bilgi için: hunspell öneri listesi kelime sınıfındaki gerçek hataların doğrusunu ilk 3'te veriyor mu?"""
    kelime_hatalari = [g for g in gercek_hatalar if g["sinif"] == "kelime"]
    sonuclar = []
    ilk3_sayisi = 0

    for g in kelime_hatalari:
        yanlis = g["kitaptaki"].strip().lstrip("’'")
        dogru = g["onerilen"].strip()
        oneriler = list(itertools.islice(sozluk.suggest(yanlis), 5))
        ilk3 = [tr_kucuk(x) for x in oneriler[:3]]
        bulundu = tr_kucuk(dogru) in ilk3
        if bulundu:
            ilk3_sayisi += 1
        sonuclar.append({
            "id": g["id"],
            "kitaptaki": g["kitaptaki"],
            "dogrusu": dogru,
            "hunspell_gecerli_mi": hunspell_gecerli_mi(sozluk, yanlis),
            "hunspell_ilk5_oneri": oneriler,
            "ilk3_icinde": bulundu,
        })

    return {
        "kelime_sinifi_toplam": len(kelime_hatalari),
        "ilk3_dogru_sayisi": ilk3_sayisi,
        "maddeler": sonuclar,
    }


if __name__ == "__main__":
    print(f"Hunspell sözlüğü yükleniyor ({SOZLUK_YOLU})...", flush=True)
    t_bas = time.perf_counter()
    sozluk = Dictionary.from_files(str(SOZLUK_YOLU))
    print(f"Hunspell yüklendi ({time.perf_counter() - t_bas:.2f} sn).", flush=True)

    sayfalar = sayfalari_yukle()
    gercek_hatalar, kurul_degil = a_verisini_yukle()
    mevcut = mevcut_sistem_sonuclari()
    mevcut_id = set(mevcut["bulunan_id"])

    res_a = bolum_a_suzgec(sozluk)
    print(
        f"(a) Süzgeç (Hakemli B): DEGIL inen {res_a['hakemli_gosterilen']['degil_inen_sayisi']}/"
        f"{res_a['hakemli_gosterilen']['degil_toplam']} (%{100*res_a['hakemli_gosterilen']['degil_inen_oran']:.1f}), "
        f"HATA kaybı {res_a['hakemli_gosterilen']['hata_kayip_sayisi']}/{res_a['hakemli_gosterilen']['hata_toplam']} "
        f"-> {res_a['hakemli_gosterilen']['karar']}"
    )
    print(
        f"(a) Süzgeç (Birleşik B): DEGIL inen {res_a['birlesik_b']['degil_inen_sayisi']}/"
        f"{res_a['birlesik_b']['degil_toplam']} (%{100*res_a['birlesik_b']['degil_inen_oran']:.1f}), "
        f"HATA kaybı {res_a['birlesik_b']['hata_kayip_sayisi']}/{res_a['birlesik_b']['hata_toplam']} "
        f"-> {res_a['birlesik_b']['karar']}"
    )

    res_b = bolum_b_bulucu(sozluk, sayfalar, gercek_hatalar, kurul_degil, mevcut_id)
    flt = res_b["ana_sonuc_filtreli"]
    ham = res_b["ham_sonuc_tum_bloklar"]
    print(
        f"(b) Bulucu (Filtreli): kelime sınıfı {flt['sinif_bulunan']['kelime']}/{flt['sinif_toplam']['kelime']}, "
        f"toplam {flt['bulunan_sayisi']}/44, eşleşmeyen {flt['eslesmeyen_isaret_toplam']} "
        f"({flt['sayfa_basi_eslesmeyen_isaret']:.2f}/sayfa) -> {flt['karar']}"
    )
    print(
        f"(b) Bulucu (Ham):      kelime sınıfı {ham['sinif_bulunan']['kelime']}/{ham['sinif_toplam']['kelime']}, "
        f"toplam {ham['bulunan_sayisi']}/44, eşleşmeyen {ham['eslesmeyen_isaret_toplam']} "
        f"({ham['sayfa_basi_eslesmeyen_isaret']:.2f}/sayfa) -> {ham['karar']}"
    )

    res_c = bolum_c_oneriler(sozluk, gercek_hatalar)
    print(f"(c) Öneri kalitesi (ilk 3): {res_c['ilk3_dogru_sayisi']}/{res_c['kelime_sinifi_toplam']}")

    cikti = {
        "arac": "hunspell-tr (spylls)",
        "bolum_a_suzgec": res_a,
        "bolum_b_bulucu": res_b,
        "bolum_c_oneriler": res_c,
    }
    (CIKTI_KLASOR / "arac2_hunspell.json").write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
