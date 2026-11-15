"""K43: Yerel modelin (gemma4) 30 A sayfasındaki adaylarını ön kayıt kuralıyla sayar."""
import json
import random
import re
import sys
from pathlib import Path

PROJE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE))
sys.stdout.reconfigure(encoding="utf-8")

from derskitabi.kriterler.yazim import tr_kucuk


def norm(metin: str) -> str:
    """Boşluk ve büyük/küçük harf farkını kaldırır; kıvrık kesme/tırnakları düzleştirir."""
    m = tr_kucuk(metin or "")
    m = m.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", "", m)


def hedef_varyantlari(kitaptaki: str) -> list[str]:
    """K42 birleştirmesinde eklenen parantez içi açıklamalar varsa asıl yazımı da döndürür."""
    n_tam = norm(kitaptaki)
    varyantlar = [n_tam] if n_tam else []
    if " (" in kitaptaki:
        ana = norm(kitaptaki.split(" (", 1)[0])
        if ana and ana not in varyantlar:
            varyantlar.append(ana)
    return varyantlar


def eslesir_mi(model_kitaptaki: str, hedef_kitaptaki: str) -> bool:
    """Ön kayıt eşleşme kuralı: biri diğerini içeriyorsa (boşluk ve harf büyüklüğü hariç) True."""
    m = norm(model_kitaptaki)
    if len(m) < 2:
        return False
    for h in hedef_varyantlari(hedef_kitaptaki):
        if len(h) >= 2 and (m in h or h in m):
            return True
    return False


def main() -> None:
    v_bag = PROJE / "veri" / "bagimsiz2"
    cikti_yolu = PROJE / "veri" / "k43" / "cikti.json"
    ozet_yolu = PROJE / "veri" / "k43" / "ozet.json"

    veri = json.loads(cikti_yolu.read_text(encoding="utf-8"))
    a_maddeler = {
        x["no"]: x
        for x in json.loads((v_bag / "A_birlesik_anahtar.json").read_text(encoding="utf-8"))["maddeler"]
    }
    kurul_anahtar = {
        m["kaynak_no"]: m["kimlik"]
        for m in json.loads((v_bag / "kurul_anahtar.json").read_text(encoding="utf-8"))
        if m["kaynak_no"].startswith("A")
    }
    kurul_sonuc = json.loads((v_bag / "kurul_sonuc.json").read_text(encoding="utf-8"))["sonuc"]

    gercek_hatalar = []
    kurul_degil = []
    for no, m in sorted(a_maddeler.items()):
        kimlik = kurul_anahtar[no]
        etiket = kurul_sonuc[kimlik]
        kayit = {**m, "kimlik": kimlik, "etiket": etiket}
        if etiket == "HATA":
            gercek_hatalar.append(kayit)
        else:
            kurul_degil.append(kayit)

    assert len(gercek_hatalar) == 17, f"17 gerçek hata bekleniyordu, {len(gercek_hatalar)} bulundu"

    sayfa_adaylari = {s["kod"]: s["adaylar"] for s in veri["sayfalar"]}

    # 1. 17 gerçek hatanın kaçı bulundu?
    bulunan_hatalar = []
    kacan_hatalar = []
    for gh in gercek_hatalar:
        adaylar = sayfa_adaylari.get(gh["sayfa"], [])
        eslesen = [a for a in adaylar if eslesir_mi(a.get("kitaptaki", ""), gh["kitaptaki"])]
        if eslesen:
            bulunan_hatalar.append({"hata": gh, "eslesen_adaylar": eslesen})
        else:
            kacan_hatalar.append(gh)

    # 2. Modelin tüm adaylarını sınıflandır
    tum_adaylar = []
    gercek_eslesen_aday_sayisi = 0
    degil_eslesen_adaylar = []
    tamamen_yeni_adaylar = []

    for s in veri["sayfalar"]:
        kod = s["kod"]
        s_gercek = [g for g in gercek_hatalar if g["sayfa"] == kod]
        s_degil = [d for d in kurul_degil if d["sayfa"] == kod]

        for a in s["adaylar"]:
            k_metin = a.get("kitaptaki", "")
            kayit_a = {"sayfa": kod, "baslik": s["baslik"], **a}
            tum_adaylar.append(kayit_a)

            es_g = [g for g in s_gercek if eslesir_mi(k_metin, g["kitaptaki"])]
            if es_g:
                gercek_eslesen_aday_sayisi += 1
                continue

            es_d = [d for d in s_degil if eslesir_mi(k_metin, d["kitaptaki"])]
            if es_d:
                degil_eslesen_adaylar.append({**kayit_a, "kurul_degil_no": [d["no"] for d in es_d]})
            else:
                tamamen_yeni_adaylar.append(kayit_a)

    bos_adaylar = degil_eslesen_adaylar + tamamen_yeni_adaylar
    rng = random.Random(20261115)
    ornek_bos_adaylar = rng.sample(bos_adaylar, min(10, len(bos_adaylar)))

    # 3. Süre ve sayfa başına ortalamalar
    sayfa_sayisi = len(veri["sayfalar"])
    toplam_aday = len(tum_adaylar)
    sayfa_basi_aday = toplam_aday / sayfa_sayisi
    sureler = [s["sure_sn"] for s in veri["sayfalar"]]
    toplam_sure = sum(sureler)
    sayfa_basi_sure = toplam_sure / sayfa_sayisi
    kitap_300_dk = (sayfa_basi_sure * 300) / 60

    bulunan_sayi = len(bulunan_hatalar)
    if bulunan_sayi >= 9 and sayfa_basi_aday < 5.0:
        karar = "Devam"
    elif bulunan_sayi <= 8:
        karar = "Kapat"
    else:
        karar = "Belirsiz"

    ozet = {
        "karar": karar,
        "bulunan_gercek_hata_sayisi": bulunan_sayi,
        "toplam_gercek_hata": len(gercek_hatalar),
        "toplam_aday": toplam_aday,
        "sayfa_basi_aday": round(sayfa_basi_aday, 2),
        "gercek_hatayla_eslesen_aday": gercek_eslesen_aday_sayisi,
        "bos_aday_toplam": len(bos_adaylar),
        "kurul_degil_ile_ayni": len(degil_eslesen_adaylar),
        "tamamen_yeni_aday": len(tamamen_yeni_adaylar),
        "toplam_sure_sn": round(toplam_sure, 2),
        "sayfa_basi_sure_sn": round(sayfa_basi_sure, 2),
        "en_kisa_sure_sn": round(min(sureler), 2),
        "en_uzun_sure_sn": round(max(sureler), 2),
        "tahmini_300_sayfa_dk": round(kitap_300_dk, 1),
        "teknik_hatalar": veri.get("teknik_hatalar", []),
        "bulunan_hatalar": bulunan_hatalar,
        "kacan_hatalar": kacan_hatalar,
        "ornek_10_bos_aday": ornek_bos_adaylar,
    }
    ozet_yolu.write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== K43 SAYIM SONUÇLARI ===")
    print(f"Ön kayıt kararı: {karar}")
    print(f"Bulunan gerçek hata: {bulunan_sayi} / {len(gercek_hatalar)} (%{100 * bulunan_sayi / len(gercek_hatalar):.1f})")
    print(f"Toplam üretilen aday: {toplam_aday} (sayfa başına ortalama: {sayfa_basi_aday:.2f})")
    print(f"  - Gerçek hatayla eşleşen aday sayısı: {gercek_eslesen_aday_sayisi}")
    print(f"  - Gerçek hatayla eşleşmeyen (boş) aday sayısı: {len(bos_adaylar)}")
    print(f"      * Kurulun DEGIL dediği adaylarla aynı: {len(degil_eslesen_adaylar)}")
    print(f"      * Tamamen yeni (kurul listesinde olmayan): {len(tamamen_yeni_adaylar)}")
    print(f"Süre: 30 sayfa toplam {toplam_sure:.1f} sn | sayfa başına ortalama {sayfa_basi_sure:.2f} sn (min {min(sureler):.2f}, maks {max(sureler):.2f} sn)")
    print(f"300 sayfalık kitap için tahmini süre: {kitap_300_dk:.1f} dakika ({kitap_300_dk / 60:.2f} saat)")

    print("\n--- BULUNAN GERÇEK HATALAR ---")
    for b in bulunan_hatalar:
        h = b["hata"]
        es = b["eslesen_adaylar"][0]
        print(f"  [+] {h['no']} ({h['kimlik']}) {h['sayfa']} s.{h['sayfa_no']}: «{h['kitaptaki']}» -> model: «{es['kitaptaki']}» (öneri: «{es['onerilen']}»)")

    print("\n--- KAÇAN GERÇEK HATALAR ---")
    for h in kacan_hatalar:
        print(f"  [-] {h['no']} ({h['kimlik']}) {h['sayfa']} s.{h['sayfa_no']}: «{h['kitaptaki']}» (doğrusu: «{h['onerilen']}»)")

    print("\n--- 10 RASTGELE BOŞ ADAY ÖRNEĞİ (Tohum 20261115) ---")
    for i, a in enumerate(ornek_bos_adaylar, 1):
        tur = f"Kurul DEGIL ({','.join(a['kurul_degil_no'])})" if "kurul_degil_no" in a else "Tamamen yeni"
        print(f"  {i:2d}. {a['sayfa']} ({a['baslik']}) [{tur}]: «{a['kitaptaki']}» -> «{a['onerilen']}» | {a['gerekce']}")


if __name__ == "__main__":
    main()
