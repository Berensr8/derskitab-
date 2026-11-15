"""K43: 30 A sayfasını yerel modele (gemma4:12b-it-qat) okutma denemesi."""
import json
import sys
import time
from pathlib import Path

PROJE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJE))
sys.stdout.reconfigure(encoding="utf-8")

from derskitabi import yerel_model

MODEL = "gemma4:12b-it-qat"
NUM_CTX = 4096
NUM_PREDICT = 1024
AZAMI_KARAKTER = 4000

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
    """Uzun sayfa metnini paragraf sınırından bölerek sinir karakter altındaki parçalara ayırır."""
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


def sayfalari_oku() -> list[dict]:
    """A_30_sayfa_metin.txt ve A_sayfa_listesi.json dosyalarından 30 sayfayı okur."""
    liste_yolu = PROJE / "bagimsiz_degerlendirme2" / "A_sayfa_listesi.json"
    metin_yolu = PROJE / "bagimsiz_degerlendirme2" / "A_30_sayfa_metin.txt"
    bilgi = {x["kod"]: x for x in json.loads(liste_yolu.read_text(encoding="utf-8"))}
    ham = metin_yolu.read_text(encoding="utf-8")
    sayfalar = []
    for blok in ham.split("===== ")[1:]:
        ust, govde = blok.split(" =====\n", 1)
        kod, baslik = [x.strip() for x in ust.split("|", 1)]
        sayfalar.append({
            "kod": kod,
            "baslik": baslik,
            "kitap": bilgi[kod]["kitap"],
            "sayfa_no": bilgi[kod]["sayfa_no"],
            "metin": govde.strip(),
        })
    return sayfalar


def main() -> None:
    cikti_yolu = PROJE / "veri" / "k43" / "cikti.json"
    cikti_yolu.parent.mkdir(parents=True, exist_ok=True)

    sayfalar = sayfalari_oku()
    assert len(sayfalar) == 30, f"30 sayfa bekleniyordu, {len(sayfalar)} bulundu"

    print(f"Model belleğe yükleniyor ({MODEL})...", flush=True)
    t_isitma = time.perf_counter()
    yerel_model.yalniz_bu_model(MODEL)
    yerel_model.sohbet(MODEL, "Hazır mısın?", "Merhaba", {"ok": {"type": "string"}}, num_predict=8, num_ctx=NUM_CTX)
    isitma_sn = round(time.perf_counter() - t_isitma, 2)
    print(f"Model hazır ({isitma_sn} sn).", flush=True)

    sonuclar = []
    teknik_hatalar = []
    t_toplam = time.perf_counter()

    for s in sayfalar:
        kod = s["kod"]
        parcalar = parcalara_bol(s["metin"])
        t0 = time.perf_counter()
        adaylar = []
        parca_hatasi = False

        for p_idx, parca in enumerate(parcalar, 1):
            soru = SORU_SABLONU.format(baslik=s["baslik"], metin=parca)
            cevap = yerel_model.sohbet(
                MODEL,
                SISTEM,
                soru,
                OZELLIKLER,
                num_predict=NUM_PREDICT,
                num_ctx=NUM_CTX,
            )
            if cevap is None or not isinstance(cevap.get("hatalar"), list):
                parca_hatasi = True
                teknik_hatalar.append({"kod": kod, "parca": p_idx, "sebep": "JSON çözülemedi veya şema dışı"})
            else:
                for h in cevap["hatalar"]:
                    if isinstance(h, dict):
                        adaylar.append({
                            "kitaptaki": str(h.get("kitaptaki", "")).strip(),
                            "onerilen": str(h.get("onerilen", "")).strip(),
                            "gerekce": str(h.get("gerekce", "")).strip(),
                        })

        sure_sn = round(time.perf_counter() - t0, 2)
        kayit = {
            "kod": kod,
            "kitap": s["kitap"],
            "sayfa_no": s["sayfa_no"],
            "baslik": s["baslik"],
            "karakter_sayisi": len(s["metin"]),
            "parca_sayisi": len(parcalar),
            "sure_sn": sure_sn,
            "json_hatasi": parca_hatasi,
            "aday_sayisi": len(adaylar),
            "adaylar": adaylar,
        }
        sonuclar.append(kayit)
        print(f"  {kod} ({s['baslik']}): {len(adaylar)} aday, {sure_sn:.2f} sn" + (" [JSON HATASI]" if parca_hatasi else ""), flush=True)

        toplam_sn = round(time.perf_counter() - t_toplam, 2)
        cikti_yolu.write_text(
            json.dumps(
                {
                    "model": MODEL,
                    "num_ctx": NUM_CTX,
                    "num_predict": NUM_PREDICT,
                    "sistem_istemi": SISTEM,
                    "soru_sablonu": SORU_SABLONU,
                    "isitma_sn": isitma_sn,
                    "toplam_sure_sn": toplam_sn,
                    "teknik_hatalar": teknik_hatalar,
                    "sayfalar": sonuclar,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"\nTamamlandı: 30 sayfa, toplam {round(time.perf_counter() - t_toplam, 2)} sn.", flush=True)


if __name__ == "__main__":
    main()
