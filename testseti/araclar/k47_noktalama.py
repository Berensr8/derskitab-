"""K47 Araç 1: Noktalama modeli (ytu-ce-cosmos/turkish-base-bert-punctuation-correction) taraması."""
import json
import re
import time

import torch
from transformers import AutoTokenizer, BertForTokenClassification

from k47_ortak import CIKTI_KLASOR, PROJE, a_verisini_yukle, arac_degerlendir, mevcut_sistem_sonuclari, sayfalari_yukle

from derskitabi.kayit import bloklari_yukle
from derskitabi.kriterler import alinti
from derskitabi.kriterler.okunabilirlik import cumlelere_bol

MODEL_YOLU = PROJE / "modeller" / "ytu-ce-cosmos__turkish-base-bert-punctuation-correction"
KELIME_RE = re.compile(r"[0-9A-Za-zÇĞİÖŞÜçğıöşüâîûÂÎÛ]+(?:['’‘-][0-9A-Za-zÇĞİÖŞÜçğıöşüâîûÂÎÛ]+)*")


def kelime_on_isle(kelime: str) -> str:
    """Model README'sindeki preprocess mantığı: kesme ve tire boşluğa çevrilir, I->ı ve lower()."""
    temiz = "".join(c for c in kelime if c.isalnum() or c in "'’‘-")
    temiz = temiz.replace("'", " ").replace("’", " ").replace("‘", " ").replace("-", " ")
    return temiz.replace("I", "ı").lower().strip()


def cumle_analiz_et(cumle: str, tokenizer, model, id2label: dict[int, str], cihaz: str) -> list[dict]:
    """Bir cümledeki her kelimenin (son kelime hariç) son alt parçasındaki noktalama tahminini döndürür."""
    eslesmeler = list(KELIME_RE.finditer(cumle))
    if len(eslesmeler) < 2:
        return []

    alt_parcalar = []
    kelime_son_indeks = []
    gecerli_eslesmeler = []

    for m in eslesmeler:
        islenmis = kelime_on_isle(m.group(0))
        if not islenmis:
            continue
        toks = tokenizer.tokenize(islenmis)
        if not toks:
            continue
        alt_parcalar.extend(toks)
        kelime_son_indeks.append(len(alt_parcalar) - 1)
        gecerli_eslesmeler.append(m)

    if len(gecerli_eslesmeler) < 2 or not alt_parcalar:
        return []

    # BERT max_position_embeddings = 512 ([CLS] ve [SEP] dahil -> en çok 510 alt parça)
    alt_parcalar = alt_parcalar[:510]
    input_ids = tokenizer.convert_tokens_to_ids(["[CLS]"] + alt_parcalar + ["[SEP]"])
    tensor_in = torch.tensor([input_ids], dtype=torch.long, device=cihaz)

    with torch.no_grad():
        logits = model(tensor_in).logits[0]  # (seq_len, num_labels)
        olasiliklar = torch.softmax(logits, dim=-1).cpu().tolist()

    sonuclar = []
    # Son kelime (cümle sonu) değerlendirilmez
    for i in range(len(gecerli_eslesmeler) - 1):
        son_idx = kelime_son_indeks[i]
        if son_idx >= 510:
            break
        # +1 çünkü 0. indeks [CLS]
        probs = olasiliklar[son_idx + 1]
        en_iyi_id = max(range(len(probs)), key=lambda idx: probs[idx])
        tahmin = id2label[en_iyi_id]
        en_iyi_olasilik = probs[en_iyi_id]
        non_id = next(idx for idx, lbl in id2label.items() if lbl == "non")
        non_olasilik = probs[non_id]

        m_sol = gecerli_eslesmeler[i]
        m_sag = gecerli_eslesmeler[i + 1]
        ara = cumle[m_sol.end():m_sag.start()]
        kitap_isaretler = [c for c in ara if c in ",;:?!."]
        kitap_isaret = kitap_isaretler[0] if kitap_isaretler else ""

        iki_kelime_parca = cumle[m_sol.start():m_sag.end()]
        sonuclar.append({
            "kelime": m_sol.group(0),
            "sonraki_kelime": m_sag.group(0),
            "iki_kelime_parca": iki_kelime_parca,
            "kitap_isaret": kitap_isaret,
            "tahmin": tahmin,
            "olasilik": en_iyi_olasilik,
            "non_olasilik": non_olasilik,
        })
    return sonuclar


def main() -> None:
    sayfalar = sayfalari_yukle()
    gercek_hatalar, kurul_degil = a_verisini_yukle()
    mevcut = mevcut_sistem_sonuclari()
    mevcut_id = set(mevcut["bulunan_id"])

    # Her kitabın alıntı/replik bloklarını hesapla
    kitap_alinti: dict[str, set[tuple[int, int]]] = {}
    for kitap in {s["kitap"] for s in sayfalar}:
        tum_bl = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        hedef_sno = {
            s["sayfa_no"] + i
            for s in sayfalar
            if s["kitap"] == kitap
            for i in range(alinti.ALINTI_EN_FAZLA_SAYFA)
        }
        ilgili = [b for b in tum_bl if b.sayfa_no in hedef_sno]
        pdf_yolu = PROJE / "veri" / f"{kitap}.pdf"
        bicimler = alinti.blok_bicimleri(pdf_yolu, ilgili) if pdf_yolu.exists() else {}
        kitap_alinti[kitap] = set(alinti.alinti_bloklari(ilgili, bicimler).keys())

    cihaz = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Noktalama modeli yükleniyor ({MODEL_YOLU.name}, cihaz={cihaz})...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_YOLU))
    model = BertForTokenClassification.from_pretrained(str(MODEL_YOLU)).to(cihaz)
    model.eval()
    id2label = {int(k): v for k, v in model.config.id2label.items()}

    t0 = time.perf_counter()
    sayfa_ham_tahminler: dict[str, list[dict]] = {s["sayfa_id"]: [] for s in sayfalar}

    for s in sayfalar:
        sid = s["sayfa_id"]
        alinti_kumesi = kitap_alinti[s["kitap"]]
        for b in s["bloklar"]:
            if b.tur != "paragraf":
                continue
            if (b.sayfa_no, b.blok_no) in alinti_kumesi:
                continue
            for cumle in cumlelere_bol(b.metin):
                for kayit in cumle_analiz_et(cumle, tokenizer, model, id2label, cihaz):
                    sayfa_ham_tahminler[sid].append({"blok_no": b.blok_no, **kayit})

    sure_sn = round(time.perf_counter() - t0, 2)
    print(f"60 sayfa noktalama taraması bitti: {sure_sn} sn (sayfa başına {sure_sn / 60:.2f} sn)", flush=True)

    esik_sonuclari = {}
    for esik in (0.90, 0.95, 0.99):
        sayfa_adaylari: dict[str, list[dict]] = {s["sayfa_id"]: [] for s in sayfalar}
        for sid, liste in sayfa_ham_tahminler.items():
            for k in liste:
                kitap_is = k["kitap_isaret"]
                tahmin = k["tahmin"]
                # Eksik: model , ; : ? tahmin ediyor (olasılık >= eşik), kitapta o kelimeden sonra işaret yok
                if not kitap_is and tahmin in {",", ";", ":", "?"} and k["olasilik"] >= esik:
                    sayfa_adaylari[sid].append({
                        "kitaptaki": k["iki_kelime_parca"],
                        "onerilen": f"{k['kelime']}{tahmin} {k['sonraki_kelime']}",
                        "gerekce": f"Eksik '{tahmin}' (p={k['olasilik']:.3f})",
                        "tur": "eksik",
                        "olasilik": round(k["olasilik"], 4),
                    })
                # Fazla: kitapta kelimeden sonra , ya da ; var, model non diyor (olasılık >= eşik)
                elif kitap_is in {",", ";"} and tahmin == "non" and k["non_olasilik"] >= esik:
                    sayfa_adaylari[sid].append({
                        "kitaptaki": k["iki_kelime_parca"],
                        "onerilen": f"{k['kelime']} {k['sonraki_kelime']}",
                        "gerekce": f"Fazla '{kitap_is}' -> non (p={k['non_olasilik']:.3f})",
                        "tur": "fazla",
                        "olasilik": round(k["non_olasilik"], 4),
                    })

        deg = arac_degerlendir(sayfa_adaylari, gercek_hatalar, kurul_degil, mevcut_id)
        nokt_bul = deg["sinif_bulunan"]["noktalama"]
        nokt_top = deg["sinif_toplam"]["noktalama"]
        gecti = (nokt_bul >= (nokt_top / 2)) and (deg["sayfa_basi_eslesmeyen_isaret"] < 1.0)
        deg["karar"] = "Geçti" if gecti else "Kapatıldı"
        deg["esik"] = esik
        esik_sonuclari[str(esik)] = deg
        print(
            f"  Eşik {esik:.2f}: noktalama sınıfı {nokt_bul}/{nokt_top}, "
            f"toplam bulunan {deg['bulunan_sayisi']}/44 (ek: {deg['mevcut_sistemin_bulmadigi_ama_aracin_buldugu']}), "
            f"eşleşmeyen {deg['eslesmeyen_isaret_toplam']} ({deg['sayfa_basi_eslesmeyen_isaret']:.2f}/sayfa) -> {deg['karar']}"
        )

    cikti = {
        "arac": "ytu-ce-cosmos/turkish-base-bert-punctuation-correction",
        "sure_sn": sure_sn,
        "sayfa_basi_sure_sn": round(sure_sn / 60, 3),
        "tahmini_300_sayfa_dk": round((sure_sn / 60) * 300 / 60, 2),
        "ana_esik": 0.95,
        "karar": esik_sonuclari["0.95"]["karar"],
        "esikler": esik_sonuclari,
    }
    (CIKTI_KLASOR / "arac1_noktalama.json").write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
