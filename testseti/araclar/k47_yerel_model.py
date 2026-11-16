"""K47 Araç 3: Yerel modelle sayfa okuma (temiz blok metniyle) — qwen3.5:9b ve gemma4:12b-it-qat."""
import json
import sys
import time

from k47_ortak import CIKTI_KLASOR, a_verisini_yukle, arac_degerlendir, mevcut_sistem_sonuclari, sayfalari_yukle

from derskitabi import yerel_model

NUM_CTX = 4096
NUM_PREDICT = 1024
AZAMI_KARAKTER = 4000

# K43 ile birebir aynı sistem istemi, soru şablonu ve JSON şeması (testseti/k43_on_kayit.md)
SISTEM = (
    "Sen Türkçe ders kitapları için çalışan bir yazım editörüsün. Bu ders kitabı sayfasında "
    "yazım, noktalama, dizgi ve yanlış kullanılmış kelime hatalarını bul. Eski metin "
    "alıntılarını, şiirleri ve ağız özelliklerini hata sayma. Her hata için kitaptaki hâlini, "
    "önerini ve kısa gerekçeni ver. Emin değilsen yazma. Sayfada hata yoksa boş liste döndür."
)

SORU_SABLONU = """Kitap ve sayfa: {baslik}

Sayfa metni:
{metin}"""

OZELLIKLER = {
    "hatalar": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "kitaptaki": {"type": "string"},
                "onerilen": {"type": "string"},
                "gerekce": {"type": "string"},
            },
            "required": ["kitaptaki", "onerilen", "gerekce"],
        },
    }
}


def parcalara_bol(metin: str, sinir: int = AZAMI_KARAKTER) -> list[str]:
    if len(metin) <= sinir:
        return [metin]
    parcalar, mevcut = [], []
    mevcut_uzunluk = 0
    for paragraf in metin.split("\n\n"):
        ek = len(paragraf) + (2 if mevcut else 0)
        if mevcut and mevcut_uzunluk + ek > sinir:
            parcalar.append("\n\n".join(mevcut))
            mevcut = [paragraf]
            mevcut_uzunluk = len(paragraf)
        else:
            mevcut.append(paragraf)
            mevcut_uzunluk += ek
    if mevcut:
        parcalar.append("\n\n".join(mevcut))
    return parcalar


def modeli_calistir(model_adi: str, sayfalar: list[dict], gercek_hatalar: list[dict], kurul_degil: list[dict], mevcut_id: set[str]) -> dict:
    dosya_adi = "arac3_" + model_adi.replace(":", "_").replace(".", "_") + ".json"
    cikti_yolu = CIKTI_KLASOR / dosya_adi

    print(f"\n=== Model belleğe yükleniyor: {model_adi} ===", flush=True)
    t_isitma = time.perf_counter()
    yerel_model.yalniz_bu_model(model_adi)
    yerel_model.sohbet(model_adi, "Hazır mısın?", "Merhaba", {"ok": {"type": "string"}}, num_predict=8, num_ctx=NUM_CTX)
    isitma_sn = round(time.perf_counter() - t_isitma, 2)
    print(f"Model hazır ({isitma_sn} sn).", flush=True)

    sayfa_kayitlari = []
    sayfa_adaylari: dict[str, list[dict]] = {}
    teknik_hatalar = []
    t_toplam = time.perf_counter()

    for idx, s in enumerate(sayfalar, 1):
        sid = s["sayfa_id"]
        # Sayfa metni: o sayfanın bloklarının metni, okuma sırasıyla, alıntı/replik blokları dahil
        temiz_metin = "\n\n".join(b.metin for b in s["bloklar"] if b.metin.strip())
        parcalar = parcalara_bol(temiz_metin)

        t0 = time.perf_counter()
        adaylar = []
        parca_hatasi = False

        for p_idx, parca in enumerate(parcalar, 1):
            soru = SORU_SABLONU.format(baslik=s["baslik"], metin=parca)
            cevap = yerel_model.sohbet(
                model_adi,
                SISTEM,
                soru,
                OZELLIKLER,
                num_predict=NUM_PREDICT,
                num_ctx=NUM_CTX,
            )
            if cevap is None or not isinstance(cevap.get("hatalar"), list):
                parca_hatasi = True
                teknik_hatalar.append({"sayfa_id": sid, "parca": p_idx, "sebep": "JSON çözülemedi veya şema dışı"})
            else:
                for h in cevap["hatalar"]:
                    if isinstance(h, dict):
                        adaylar.append({
                            "kitaptaki": str(h.get("kitaptaki", "")).strip(),
                            "onerilen": str(h.get("onerilen", "")).strip(),
                            "gerekce": str(h.get("gerekce", "")).strip(),
                        })

        sure_sn = round(time.perf_counter() - t0, 2)
        sayfa_adaylari[sid] = adaylar
        sayfa_kayitlari.append({
            "sayfa_id": sid,
            "kitap": s["kitap"],
            "sayfa_no": s["sayfa_no"],
            "baslik": s["baslik"],
            "karakter_sayisi": len(temiz_metin),
            "parca_sayisi": len(parcalar),
            "sure_sn": sure_sn,
            "json_hatasi": parca_hatasi,
            "aday_sayisi": len(adaylar),
            "adaylar": adaylar,
        })
        if idx % 5 == 0 or idx == len(sayfalar) or parca_hatasi:
            print(
                f"  [{idx:02d}/60] {sid} ({s['baslik']}): {len(adaylar)} aday, {sure_sn:.2f} sn"
                + (" [JSON HATASI]" if parca_hatasi else ""),
                flush=True,
            )

    toplam_sure = round(sum(x["sure_sn"] for x in sayfa_kayitlari), 2)
    sayfa_basi_sure = round(toplam_sure / len(sayfalar), 2)
    tahmini_300_dk = round((sayfa_basi_sure * 300) / 60, 1)

    deg = arac_degerlendir(sayfa_adaylari, gercek_hatalar, kurul_degil, mevcut_id)
    gecti = (
        deg["bulunan_sayisi"] >= 15
        and deg["sayfa_basi_isaret"] < 3.0
        and deg["mevcut_sistemin_bulmadigi_ama_aracin_buldugu"] >= 8
    )
    deg["karar"] = "Geçti" if gecti else "Kapatıldı"

    cikti = {
        "model": model_adi,
        "isitma_sn": isitma_sn,
        "toplam_sure_sn": toplam_sure,
        "sayfa_basi_sure_sn": sayfa_basi_sure,
        "tahmini_300_sayfa_dk": tahmini_300_dk,
        "teknik_hatalar": teknik_hatalar,
        "karar": deg["karar"],
        "degerlendirme": deg,
        "sayfalar": sayfa_kayitlari,
    }
    cikti_yolu.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"-> {model_adi} BİTTİ: bulunan {deg['bulunan_sayisi']}/44 "
        f"(ek: {deg['mevcut_sistemin_bulmadigi_ama_aracin_buldugu']}), "
        f"aday {deg['toplam_isaret']} ({deg['sayfa_basi_isaret']:.2f}/sayfa), "
        f"süre {toplam_sure:.1f} sn ({sayfa_basi_sure:.2f} sn/sayfa, 300 sayfa ~{tahmini_300_dk} dk) -> {deg['karar']}",
        flush=True,
    )
    return cikti


def main() -> None:
    sayfalar = sayfalari_yukle()
    gercek_hatalar, kurul_degil = a_verisini_yukle()
    mevcut = mevcut_sistem_sonuclari()
    mevcut_id = set(mevcut["bulunan_id"])

    modeller = sys.argv[1:] if len(sys.argv) > 1 else ["qwen3.5:9b", "gemma4:12b-it-qat"]
    for m in modeller:
        modeli_calistir(m, sayfalar, gercek_hatalar, kurul_degil, mevcut_id)


if __name__ == "__main__":
    main()
