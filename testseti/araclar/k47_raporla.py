"""K47 araç taraması sonuç raporunu (testseti/k47_sonuclari.md) üretir."""
import json
from pathlib import Path

from k47_ortak import CIKTI_KLASOR, PROJE, a_verisini_yukle


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def main() -> None:
    gercek_hatalar, kurul_degil = a_verisini_yukle()
    gh_map = {g["id"]: g for g in gercek_hatalar}

    mevcut = json.loads((CIKTI_KLASOR / "mevcut_sistem.json").read_text(encoding="utf-8"))
    a1 = json.loads((CIKTI_KLASOR / "arac1_noktalama.json").read_text(encoding="utf-8"))
    a2 = json.loads((CIKTI_KLASOR / "arac2_hunspell.json").read_text(encoding="utf-8"))
    qwen = json.loads((CIKTI_KLASOR / "arac3_qwen3_5_9b.json").read_text(encoding="utf-8"))
    gemma = json.loads((CIKTI_KLASOR / "arac3_gemma4_12b-it-qat.json").read_text(encoding="utf-8"))

    mevcut_id = set(mevcut["bulunan_id"])
    mevcut_sinif = {"noktalama": 0, "kelime": 0, "diger": 0}
    for gid in mevcut_id:
        mevcut_sinif[gh_map[gid]["sinif"]] += 1

    gemma_deg = gemma["degerlendirme"]
    gemma_id = set(gemma_deg["bulunan_id"])
    birlesik_id = mevcut_id | gemma_id
    birlesik_sinif = {"noktalama": 0, "kelime": 0, "diger": 0}
    for gid in birlesik_id:
        birlesik_sinif[gh_map[gid]["sinif"]] += 1

    # K42_A36 ('abesdir) gemma4'te kitaptaki == onerilen ("hata sayılmamıştır" açıklamasıyla) çıktığı için
    # sıkı (önerisi farklı) sayımı da ayrıca hesaplayalım
    gemma_siki_id = {gid for gid in gemma_id if gid != "K42_A36"}
    birlesik_siki_id = mevcut_id | gemma_siki_id
    birlesik_siki_sinif = {"noktalama": 0, "kelime": 0, "diger": 0}
    for gid in birlesik_siki_id:
        birlesik_siki_sinif[gh_map[gid]["sinif"]] += 1

    lines = []
    lines.append("# K47: Yeni Araçların Taraması Sonuçları")
    lines.append("")
    lines.append("- **Tarih:** 2026-11-16")
    lines.append("- **Ön kayıt:** `testseti/k47_on_kayit.md` (`f5013d5` commit'i ile araçlar çalıştırılmadan önce kilitlendi)")
    lines.append("- **Veri:** K42 (30 sayfa, 17 gerçek hata) + K45 (30 sayfa, 27 gerçek hata) = **60 A sayfası**, **44 gerçek hata** (`HATA`), **106 kurul reddi** (`DEGIL` / `BELIRSIZ`).")
    lines.append("- **Metin kaynağı:** `veri/<kitap>_bloklar.json` (ürünün yumuşak tireleri temizlenmiş kendi blokları; `A_30_sayfa_metin.txt` kullanılmadı).")
    lines.append(
        f"- **Mevcut sistem (`HEAD`, `ce96bf8`):** 60 sayfada güven $\\ge 0,5$ ile gösterilen tespitler 44 gerçek hatanın "
        f"**15'ini (%34,1)** yakalıyor (`noktalama`: {mevcut_sinif['noktalama']}/13, `kelime`: {mevcut_sinif['kelime']}/9, `diger`: {mevcut_sinif['diger']}/22)."
    )
    lines.append("")
    lines.append("## 1. Özet Karar Tablosu")
    lines.append("")
    lines.append("| Araç | Alt Görev / Model | Ana Ölçütler | Sonuç | Süre (60 sayfa) | Karar |")
    lines.append("|---|---|---|---|---|---|")

    a1_95 = a1["esikler"]["0.95"]
    lines.append(
        f"| **Araç 1** | `ytu-ce-cosmos/turkish-base-bert-punctuation-correction` (eşik 0,95) | "
        f"Noktalama $\\ge 7/13$ **ve** eşleşmeyen $< 1,0$/sayfa | "
        f"Noktalama **4/13**, eşleşmeyen **4,87/sayfa** (292 adet) | {a1['sure_sn']} sn (0,17 sn/sayfa) | **Kapatıldı** ✗ |"
    )

    a2_a_hak = a2["bolum_a_suzgec"]["hakemli_gosterilen"]
    a2_a_bir = a2["bolum_a_suzgec"]["birlesik_b"]
    lines.append(
        f"| **Araç 2 (a)** | `hunspell-tr` — Yanlış alarm süzgeci (B `morfoloji`) | "
        f"`HATA` kaybı $\\le 1$ **ve** `DEGIL` inen $\\ge \\%30$ | "
        f"Hakemli B: kayıp **1/13**, inen **11/66 (\\%16,7)**; Birleşik B: kayıp **1/18**, inen **15/124 (\\%12,1)** | < 1 sn | **Kapatıldı** ✗ |"
    )

    a2_b_flt = a2["bolum_b_bulucu"]["ana_sonuc_filtreli"]
    lines.append(
        f"| **Araç 2 (b)** | `hunspell-tr` — Bulucu (Starlang+Zemberek geçerli, Hunspell red) | "
        f"Kelime sınıfı $\\ge 3/9$ **ve** eşleşmeyen $< 1,0$/sayfa | "
        f"Kelime **1/9**, eşleşmeyen **0,37/sayfa** (22 adet; hamda 1,65/sayfa) | {a2['bolum_b_bulucu']['sure_sn']} sn | **Kapatıldı** ✗ |"
    )

    q_deg = qwen["degerlendirme"]
    lines.append(
        f"| **Araç 3 (Qwen)** | `qwen3.5:9b` (temiz blok metniyle sayfa okuma) | "
        f"Bulunan $\\ge 15/44$, ek $\\ge 8$, aday $< 3,0$/sayfa | "
        f"Bulunan **12/44**, ek **6**, aday **2,93/sayfa** (176 aday; 23 sayfada JSON hatası) | {qwen['toplam_sure_sn']} sn (17,98 sn/sayfa) | **Kapatıldı** ✗ |"
    )

    lines.append(
        f"| **Araç 3 (Gemma)** | `gemma4:12b-it-qat` (temiz blok metniyle sayfa okuma) | "
        f"Bulunan $\\ge 15/44$, ek $\\ge 8$, aday $< 3,0$/sayfa | "
        f"Bulunan **19/44** (sıkı: 18/44), ek **12** (sıkı: 11), aday **2,25/sayfa** (135 aday) | {gemma['toplam_sure_sn']} sn (15,21 sn/sayfa) | **Geçti** ✓ |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- ARAÇ 1 ---
    lines.append("## 2. Araç 1: Noktalama Modeli (`ytu-ce-cosmos/turkish-base-bert-punctuation-correction`)")
    lines.append("")
    lines.append("### 2.1. Ölçüt ve Eşik Tablosu")
    lines.append("")
    lines.append("- **Süre:** 60 sayfa toplam **9,93 sn** (sayfa başına **0,166 sn**, 300 sayfalık kitap için **~0,83 dk**).")
    lines.append("")
    lines.append("| Eşik | Noktalama Sınıfı (Ölçüt: $\\ge 7/13$) | Toplam Bulunan (/44) | Mevcut Sistemin Bulmadığı (Ek) | Toplam İşaret | Eşleşmeyen İşaret (Ölçüt: $< 60$, yani $< 1,0$/sayfa) | Kurul Reddiyle Eşleşen | Karar |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for esik_k in ("0.9", "0.95", "0.99"):
        d = a1["esikler"][esik_k]
        etiket = f"**{float(esik_k):.2f} (Ana)**" if esik_k == "0.95" else f"{float(esik_k):.2f}"
        lines.append(
            f"| {etiket} | {d['sinif_bulunan']['noktalama']}/13 | {d['bulunan_sayisi']}/44 | "
            f"{d['mevcut_sistemin_bulmadigi_ama_aracin_buldugu']} | {d['toplam_isaret']} ({d['sayfa_basi_isaret']:.2f}/s) | "
            f"{d['eslesmeyen_isaret_toplam']} (**{d['sayfa_basi_eslesmeyen_isaret']:.2f}/s**) | {d['kurul_reddi_ile_eslesen']} | **{d['karar']}** |"
        )
    lines.append("")
    lines.append("### 2.2. Bulduğu ve Kaçırdığı Gerçek Hatalar (Eşik 0,95)")
    lines.append("")
    lines.append("**Bulunan gerçek hatalar (5/44 — 4 `noktalama`, 1 mekanik bağlam eşleşmesiyle `kelime`):**")
    for b in a1_95["bulunan_hatalar"]:
        gh = b["hata"]
        es = b["eslesen_adaylar"][0]
        not_ek = " *(Not: iki kelimelik bağlam parçası `Commasie` kelimesini içerdiği için mekanik eşleşti)*" if gh["id"] == "K42_A04" else ""
        lines.append(
            f"- `{gh['id']}` (`{gh['sayfa_id']}`, `{gh['sinif']}`): kitaptaki `{gh['kitaptaki']}` $\\rightarrow$ doğrusu `{gh['onerilen']}` "
            f"| Modelin işaret ettiği: `{es['kitaptaki']}` $\\rightarrow$ `{es['onerilen']}` ({es['gerekce']}){not_ek}"
        )
    lines.append("")
    lines.append("**Kaçırılan `noktalama` sınıfı gerçek hatalar (9/13):**")
    nokt_kacan = [g for g in a1_95["kacan_hatalar"] if g["sinif"] == "noktalama"]
    for g in nokt_kacan:
        lines.append(f"- `{g['id']}` (`{g['sayfa_id']}`): `{g['kitaptaki']}` $\\rightarrow$ `{g['onerilen']}`")
    lines.append("")
    lines.append("*(Not: `yazınız..`, `Yönerge :`, `11,12, 13`, `1947,1962`, `Ksilemdeki su ,` gibi dizgi/boşluk noktalamaları model ön işlemde noktalama işaretlerini soyduğu için yapısal olarak bu modelin kapsamı dışındadır; noktalı virgülün virgüle dönüşmesi gereken `K42_A14`, `K42_A18`, `K45_A39` maddelerinde ise model `non` yerine farklı noktalama olasılıkları dağıttığı için 0,95 eşiğini geçememiştir.)*")
    lines.append("")
    lines.append("### 2.3. 10 Rastgele Eşleşmeyen İşaret Örneği (Eşik 0,95, Tohum `20261117`)")
    lines.append("")
    lines.append("| # | Sayfa | Kitaptaki Parça | Model Önerisi | Gerekçe |")
    lines.append("|---|---|---|---|---|")
    for idx, o in enumerate(a1_95["ornek_10_eslesmeyen"], 1):
        lines.append(f"| {idx} | `{o['sayfa_id']}` | `{md_escape(o['kitaptaki'])}` | `{md_escape(o['onerilen'])}` | {md_escape(o['gerekce'])} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- ARAÇ 2 ---
    lines.append("## 3. Araç 2: `hunspell-tr` (`spylls`)")
    lines.append("")
    lines.append("### 3.1. Ölçüt Tablosu — (a) Yanlış Alarm Süzgeci ve (b) Bulucu")
    lines.append("")
    lines.append("- **Sözlük yükleme süresi:** 3,98 sn; **60 sayfa tarama süresi:** **35,84 sn** (sayfa başına **0,597 sn**, 300 sayfa için **~3,0 dk**).")
    lines.append("")
    lines.append("| Kullanım | Küme | Ölçüt | Gerçekleşen | Karar |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| **(a) Yanlış alarm süzgeci** | Hakemli gösterilen B `morfoloji` (79 tespit: 13 `HATA`, 66 `DEGIL`) | "
        f"`HATA` kaybı $\\le 1$ **ve** `DEGIL` inen $\\ge \\%30$ | "
        f"`HATA` kaybı: **1/13** (`sorumluklar`), `DEGIL` inen: **11/66 (\\%16,7)** | **Kapatıldı** ✗ |"
    )
    lines.append(
        f"| **(a) Yanlış alarm süzgeci** | Birleşik B `morfoloji` (144 tespit: 18 `HATA`, 124 `DEGIL`, 2 `BELIRSIZ`) | "
        f"`HATA` kaybı $\\le 1$ **ve** `DEGIL` inen $\\ge \\%30$ | "
        f"`HATA` kaybı: **1/18** (`sorumluklar`), `DEGIL` inen: **15/124 (\\%12,1)** | **Kapatıldı** ✗ |"
    )
    lines.append(
        f"| **(b) Bulucu** | 60 A sayfası (ürün süzgeçleri sonrası) | "
        f"`kelime` sınıfı $\\ge 3/9$ **ve** eşleşmeyen $< 1,0$/sayfa | "
        f"`kelime` sınıfı: **1/9** (`K45_A29` `işaretleyiz`), eşleşmeyen: **22 (0,37/sayfa)** | **Kapatıldı** ✗ |"
    )
    lines.append(
        f"| **(b) Bulucu (Ham)** | 60 A sayfası (terim/alıntı süzgeci öncesi) | "
        f"`kelime` sınıfı $\\ge 3/9$ **ve** eşleşmeyen $< 1,0$/sayfa | "
        f"`kelime` sınıfı: **1/9** (`K45_A29` `işaretleyiz`), eşleşmeyen: **99 (1,65/sayfa)** | **Kapatıldı** ✗ |"
    )
    lines.append("")
    lines.append("### 3.2. (a) Süzgeç Ayrıntıları")
    lines.append("")
    lines.append("- **Kaybedilen gerçek hata (1 adet):** `K42_B30` (`biyoloji11` s. 139) `sorumluklar` — `hunspell-tr` sözlüğünde `sorumluk` kökü tanımlı olduğu için bu gerçek yazım hatasını geçerli saydı.")
    lines.append("- **Düşürülen yanlış alarmlar (Hakemli B'de 11/66):** " + ", ".join(f"`{x['kelime']}` (`{x['id']}`)" for x in a2_a_hak["degil_inenler"]))
    lines.append("- Yanlış alarmların geri kalan %83,3'ü (`transkripsiyonu`, `ökaryot`, `kemoototrof`, `meristem`, `siyanobakteriler`, `allosterik` vb. biyoloji terimleri ve eski Türkçe kelimeler) `hunspell-tr` sözlüğünde de yer almadığı için süzülemedi.")
    lines.append("")
    lines.append("### 3.3. (b) Bulucu: Bulunan ve Kaçırılan `kelime` Sınıfı Hatalar")
    lines.append("")
    lines.append("- **Bulunan (1/9):** `K45_A29` (`K45_S14`, `biyoloji12` s. 186): `işaretleyiz` $\\rightarrow$ `işaretleyiniz` (Starlang ve Zemberek `işaretle-y-iz` olarak çözümlediği hâlde `hunspell-tr` reddetti; mevcut sistem bunu bulamıyordu).")
    lines.append("- **Kaçırılan `kelime` sınıfı hatalar (8/9):**")
    for g in a2_b_flt["kacan_hatalar"]:
        if g["sinif"] == "kelime":
            lines.append(f"  - `{g['id']}` (`{g['sayfa_id']}`): `{g['kitaptaki']}` $\\rightarrow$ `{g['onerilen']}`")
    lines.append("  *(Not: `coğrafik` ve `kollektifleştirme` zaten Starlang/Zemberek tarafından da reddedildiği için 'Starlang+Zemberek geçerli' kümesinde değildir; `Commasie`, `Canidea`, `COVİD-19`, `Yarımada’yı` büyük harf/özel ad/kesme kurallarıyla atlanır; `gr` 2 harfli kısaltma olduğu için atlanır ve ayrıca `hunspell-tr` `gr`'yi geçerli saymaktadır; `’abesdir` ise alıntı dizesindedir ve Starlang/Zemberek tarafından da reddedilmektedir.)*")
    lines.append("")
    lines.append("### 3.4. (b) Bulucu: 10 Rastgele Eşleşmeyen İşaret Örneği (Tohum `20261117`)")
    lines.append("")
    lines.append("| # | Sayfa | Kitaptaki Kelime | Gerekçe |")
    lines.append("|---|---|---|---|")
    for idx, o in enumerate(a2_b_flt["ornek_10_eslesmeyen"], 1):
        lines.append(f"| {idx} | `{o['sayfa_id']}` | `{md_escape(o['kitaptaki'])}` | {md_escape(o['gerekce'])} |")
    lines.append("")
    lines.append("### 3.5. (c) Bilgi İçin: `hunspell-tr` Öneri Kalitesi (`kelime` Sınıfındaki 9 Gerçek Hata)")
    lines.append("")
    lines.append("`kelime` sınıfındaki 9 gerçek hatanın **4'ünde (%44,4)** doğru yazım `hunspell.suggest()` ilk 3 önerisi içinde yer aldı:")
    lines.append("")
    lines.append("| ID | Kitaptaki | Doğrusu | Hunspell Geçerli mi? | İlk 3 Öneri | İlk 3'te Doğru Var mı? |")
    lines.append("|---|---|---|---|---|---|")
    for m in a2["bolum_c_oneriler"]["maddeler"]:
        ilk3_str = ", ".join(f"`{x}`" for x in m["hunspell_ilk5_oneri"][:3]) or "*(öneri yok)*"
        gec_str = "Evet" if m["hunspell_gecerli_mi"] else "Hayır"
        bul_str = "✓ Evet" if m["ilk3_icinde"] else "✗ Hayır"
        lines.append(f"| `{m['id']}` | `{m['kitaptaki']}` | `{m['dogrusu']}` | {gec_str} | {ilk3_str} | {bul_str} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- ARAÇ 3 ---
    lines.append("## 4. Araç 3: Yerel Modelle Sayfa Okuma (Temiz Blok Metniyle)")
    lines.append("")
    lines.append("K43'teki deneyde ham `A_30_sayfa_metin.txt` içindeki yumuşak tireler (`U+00AD`) 67 adayın 50'sini sahte tire hatasına dönüştürmüştü. Bu taramada modellere doğrudan ürünün temizlenmiş blok metinleri (`veri/<kitap>_bloklar.json`) K43 ile birebir aynı sistem istemi, soru şablonu ve JSON şemasıyla (`temperature=0`, `num_ctx=4096`, `num_predict=1024`) verildi.")
    lines.append("")
    lines.append("### 4.1. Model Karşılaştırma ve Ölçüt Tablosu")
    lines.append("")
    lines.append("| Ölçüt / Gösterge | Geçme Eşiği | `qwen3.5:9b` | `gemma4:12b-it-qat` |")
    lines.append("|---|---|---|---|")
    lines.append(f"| **Bulunan gerçek hata (/44)** | $\\ge 15 / 44$ | **12 / 44** (%27,3) ✗ | **19 / 44** (%43,2; sıkı: **18 / 44**, %40,9) ✓ |")
    lines.append(f"| **Mevcut sistemin bulmadığı (ek hata)** | $\\ge 8$ | **6** ✗ | **12** (sıkı: **11**) ✓ |")
    lines.append(f"| **Toplam aday / sayfa başı aday** | $< 3,0$ / sayfa ($< 180$) | 176 (**2,93 / sayfa**) ✓ | 135 (**2,25 / sayfa**) ✓ |")
    lines.append(f"| `noktalama` sınıfı bulunan (/13) | *(Bilgi)* | 3 / 13 | 6 / 13 |")
    lines.append(f"| `kelime` sınıfı bulunan (/9) | *(Bilgi)* | 2 / 9 | 5 / 9 (sıkı: 4 / 9) |")
    lines.append(f"| `diger` sınıfı bulunan (/22) | *(Bilgi)* | 7 / 22 | 8 / 22 |")
    lines.append(f"| Eşleşmeyen aday sayısı | *(Bilgi)* | 162 (2,70 / sayfa) | 115 (1,92 / sayfa) |")
    lines.append(f"| Kurulun `DEGIL` dediğiyle eşleşen aday | *(Bilgi)* | 11 | 8 |")
    lines.append(f"| JSON şema / kesilme hatası olan sayfa | *(Bilgi)* | **23 / 60 sayfa** | **1 / 60 sayfa** (`K45_S11`) |")
    lines.append(f"| Toplam süre (60 sayfa) | *(Bilgi)* | 1078,5 sn (~18,0 dk) | 912,3 sn (~15,2 dk) |")
    lines.append(f"| Sayfa başına ortalama süre | *(Bilgi)* | **17,98 sn / sayfa** | **15,21 sn / sayfa** |")
    lines.append(f"| **300 sayfalık kitap tahmini süre** | *(Bilgi)* | **~89,9 dk (~1,5 saat)** | **~76,0 dk (~1,27 saat)** |")
    lines.append(f"| **Karar** | Tüm ölçütler ✓ | **Kapatıldı** ✗ | **Geçti** ✓ |")
    lines.append("")

    # --- 4.2 QWEN ---
    lines.append("### 4.2. `qwen3.5:9b` Ayrıntıları (Kapatıldı)")
    lines.append("")
    lines.append("**Bulunan gerçek hatalar (12/44; mevcut sistemin bulmadığı 6 hata `(+)` ile işaretli):**")
    for b in q_deg["bulunan_hatalar"]:
        gh = b["hata"]
        es = b["eslesen_adaylar"][0]
        ek_is = " `(+)`" if gh["id"] in q_deg["ek_bulunan_id"] else ""
        not_q = ""
        if gh["id"] == "K45_A17":
            not_q = " *(Not: model tablo başlığını değil, paragraftaki `'...farklı yönleri Tablo 2.6’ da...'` cümlesini kesme boşluğu için alıntıladığından `Farklı yönleri` ile mekanik eşleşti)*"
        lines.append(
            f"- `{gh['id']}`{ek_is} (`{gh['sayfa_id']}`, `{gh['sinif']}`): `{gh['kitaptaki']}` $\\rightarrow$ `{gh['onerilen']}` "
            f"| Model: `{md_escape(es['kitaptaki'])}` $\\rightarrow$ `{md_escape(es['onerilen'])}`{not_q}"
        )
    lines.append("")
    lines.append("**Kaçırılan gerçek hatalar (32/44):** " + ", ".join(f"`{g['id']}`" for g in q_deg["kacan_hatalar"]))
    lines.append("")
    lines.append("**`qwen3.5:9b` — 10 Rastgele Eşleşmeyen İşaret Örneği (Tohum `20261117`):**")
    lines.append("")
    lines.append("| # | Sayfa | Kitaptaki Parça | Model Önerisi | Gerekçe |")
    lines.append("|---|---|---|---|---|")
    for idx, o in enumerate(q_deg["ornek_10_eslesmeyen"], 1):
        lines.append(f"| {idx} | `{o['sayfa_id']}` | `{md_escape(o['kitaptaki'])}` | `{md_escape(o['onerilen'])}` | {md_escape(o['gerekce'])} |")
    lines.append("")

    # --- 4.3 GEMMA4 ---
    lines.append("### 4.3. `gemma4:12b-it-qat` Ayrıntıları (Geçti)")
    lines.append("")
    lines.append("Temiz blok metni verildiğinde `gemma4:12b-it-qat`'ın K43'teki sahte tire sorunu tamamen ortadan kalktı (K43'te 30 sayfada 67 adayın 50'si sahte tire iken, K47'de 60 sayfada 135 adayın yalnızca 1 tanesinde satır sonu tire birleşimi geçti). Model 44 gerçek hatanın **19'unu** (mekanik; `K42_A36` alıntı açıklaması çıkarıldığında **18'ini**) yakaladı ve mevcut sistemin (`HEAD`) kaçırdığı **12 gerçek hatayı** (sıkı: **11**) buldu.")
    lines.append("")
    lines.append("**Bulunan gerçek hatalar (19/44; mevcut sistemin bulmadığı 12 hata `(+)` ile işaretli):**")
    for b in gemma_deg["bulunan_hatalar"]:
        gh = b["hata"]
        # En uygun eşleşen adayı seç (ör. K45_A23 için 'Ksilemdeki su ,' olanı)
        es = b["eslesen_adaylar"][0]
        for aday_es in b["eslesen_adaylar"]:
            if gh["kitaptaki"].strip() in aday_es["kitaptaki"]:
                es = aday_es
                break
        ek_is = " `(+)`" if gh["id"] in gemma_deg["ek_bulunan_id"] else ""
        not_g = ""
        if gh["id"] == "K42_A36":
            not_g = " *(Mekanik eşleşme notu: model bu dizeyi `'şiir/eski metin alıntısı olduğu için hata olarak sayılmamıştır'` gerekçesiyle `kitaptaki == onerilen` olarak döndürdü; bu satır elendiğinde dahi 18/44 bulunan ve 11 ek hata ile tüm ölçütler sağlanmaktadır.)*"
        lines.append(
            f"- `{gh['id']}`{ek_is} (`{gh['sayfa_id']}`, `{gh['sinif']}`): `{gh['kitaptaki']}` $\\rightarrow$ `{gh['onerilen']}` "
            f"| Model: `{md_escape(es['kitaptaki'])}` $\\rightarrow$ `{md_escape(es['onerilen'])}` ({md_escape(es['gerekce'])}){not_g}"
        )
    lines.append("")
    lines.append("**Kaçırılan gerçek hatalar (25/44):**")
    for g in gemma_deg["kacan_hatalar"]:
        lines.append(f"- `{g['id']}` (`{g['sayfa_id']}`, `{g['sinif']}`): `{g['kitaptaki']}` $\\rightarrow$ `{g['onerilen']}`")
    lines.append("")
    lines.append("**`gemma4:12b-it-qat` — 10 Rastgele Eşleşmeyen İşaret Örneği (Tohum `20261117`):**")
    lines.append("")
    lines.append("| # | Sayfa | Kitaptaki Parça | Model Önerisi | Gerekçe |")
    lines.append("|---|---|---|---|---|")
    for idx, o in enumerate(gemma_deg["ornek_10_eslesmeyen"], 1):
        lines.append(f"| {idx} | `{o['sayfa_id']}` | `{md_escape(o['kitaptaki'])}` | `{md_escape(o['onerilen'])}` | {md_escape(o['gerekce'])} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- 5. BİRLEŞİK TABLO ---
    lines.append("## 5. Birleşik Tablo: Mevcut Sistem ve Mevcut Sistem + Geçen Araç (`gemma4:12b-it-qat`)")
    lines.append("")
    lines.append("Ön kayıt ölçütlerini yalnız **Araç 3 (`gemma4:12b-it-qat` ile temiz blok metni üzerinden sayfa okuma)** geçti.")
    lines.append("")
    lines.append("| Sistem Bileşimi | `noktalama` (/13) | `kelime` (/9) | `diger` (/22) | Toplam Bulunan (/44) | Bulma Oranı |")
    lines.append("|---|---|---|---|---|---|")
    lines.append(
        f"| **Mevcut sistem (`HEAD`, `ce96bf8`) tek başına** | {mevcut_sinif['noktalama']}/13 | {mevcut_sinif['kelime']}/9 | "
        f"{mevcut_sinif['diger']}/22 | **15 / 44** | **%34,1** |"
    )
    lines.append(
        f"| **`gemma4:12b-it-qat` tek başına (mekanik)** | {gemma_deg['sinif_bulunan']['noktalama']}/13 | {gemma_deg['sinif_bulunan']['kelime']}/9 | "
        f"{gemma_deg['sinif_bulunan']['diger']}/22 | **19 / 44** | **%43,2** |"
    )
    lines.append(
        f"| **`gemma4:12b-it-qat` tek başına (`kitaptaki != onerilen` süzgeçli)** | 6/13 | 4/9 | 8/22 | **18 / 44** | **%40,9** |"
    )
    lines.append(
        f"| **Mevcut sistem + `gemma4:12b-it-qat` (mekanik birleşim)** | {birlesik_sinif['noktalama']}/13 | {birlesik_sinif['kelime']}/9 | "
        f"{birlesik_sinif['diger']}/22 | **{len(birlesik_id)} / 44** | **%{100*len(birlesik_id)/44:.1f}** |"
    )
    lines.append(
        f"| **Mevcut sistem + `gemma4:12b-it-qat` (`kitaptaki != onerilen` süzgeçli)** | {birlesik_siki_sinif['noktalama']}/13 | {birlesik_siki_sinif['kelime']}/9 | "
        f"{birlesik_siki_sinif['diger']}/22 | **{len(birlesik_siki_id)} / 44** | **%{100*len(birlesik_siki_id)/44:.1f}** |"
    )
    lines.append("")
    lines.append("### 5.1. Kümelerin Kesişimi ve Tamamlayıcılığı")
    lines.append("")
    ortak_id = sorted(mevcut_id & gemma_siki_id)
    yalniz_mevcut = sorted(mevcut_id - gemma_siki_id)
    yalniz_gemma = sorted(gemma_siki_id - mevcut_id)
    ikisi_de_kacirdi = sorted(set(gh_map.keys()) - birlesik_siki_id)
    lines.append(f"- **Her ikisinin de yakaladığı ({len(ortak_id)} hata):** " + ", ".join(f"`{x}`" for x in ortak_id))
    lines.append(f"- **Yalnız mevcut sistemin (`HEAD`) yakaladığı ({len(yalniz_mevcut)} hata):** " + ", ".join(f"`{x}` (`{gh_map[x]['kitaptaki']}`)" for x in yalniz_mevcut))
    lines.append(f"- **Yalnız `gemma4:12b-it-qat`'ın yakaladığı ({len(yalniz_gemma)} gerçek hata + 1 mekanik `K42_A36`):** " + ", ".join(f"`{x}` (`{gh_map[x]['kitaptaki']}` $\\rightarrow$ `{gh_map[x]['onerilen']}`)" for x in yalniz_gemma))
    lines.append(f"- **İkisinin de kaçırdığı ({len(ikisi_de_kacirdi)} hata):** " + ", ".join(f"`{x}`" for x in ikisi_de_kacirdi))
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- 6. ÖN KAYITTAN SAPMA VE TEKNİK SORUNLAR ---
    lines.append("## 6. Ön Kayıttan Sapma ve Teknik Gözlemler")
    lines.append("")
    lines.append("1. **Ön kayıttan sapma yoktur:** `testseti/k47_on_kayit.md` içinde kilitlenen hata sınıfları, eşleşme kuralı, eşikler (`0,95`, `%30`, `15/44`, `8 ek hata`, `< 3,0 aday/sayfa`), sistem istemi ve JSON şeması hiçbir araçta değiştirilmemiştir.")
    lines.append("2. **`qwen3.5:9b` JSON kesilme sorunu:** `qwen3.5:9b`, `num_predict=1024` sınırında 60 sayfanın 23'ünde çok sayıda sahte/uzun açıklama üretmeye çalışırken JSON çıktısını tamamlayamadı (`yerel_model.sohbet` `None` döndü). K43'te de aynı model 30 sayfanın 9'unda aynı sebeple boş dönmüştü.")
    lines.append("3. **`gemma4:12b-it-qat` JSON kararlılığı ve `kitaptaki == onerilen` gözlemi:** `gemma4:12b-it-qat` 60 sayfanın 59'unda geçerli JSON döndürdü (yalnız `K45_S11` sayfasında 1 kez JSON kesildi). Ayrıca model 135 adayın 11'inde `kitaptaki` ile `onerilen` alanını birebir aynı bıraktı (ör. `K42_A36` alıntı dizesinde `'hata olarak sayılmamıştır'` açıklaması yazarak). Ürün entegrasyonunda `norm(kitaptaki) == norm(onerilen)` olan çıktılar tek satırlık mekanik süzgeçle elenebilir; bu süzgeç uygulandığında aday sayısı 135'ten 124'e (2,07/sayfa), eşleşmeyen aday sayısı 115'ten 105'e (1,75/sayfa) düşmekte ve 18/44 gerçek hata (11 ek hata) korunmaktadır.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- 7. SINIRLAMALAR ---
    lines.append("## 7. Sınırlamalar")
    lines.append("")
    lines.append("- **Görülmüş sayfalar (Tarama niteliği):** Bu çalışma bir ürün ölçümü değil, araç taramasıdır. K42 ve K45'teki 60 sayfa önceki geliştirmelerde görülmüştür. Geçen aracın (`gemma4:12b-it-qat` ile temiz blok metni okuma) gerçek isabet ve bulma oranı, ürüne eklendikten sonra **daha önce hiç görülmemiş yeni bir kitapta** bağımsız 3 modelli kurulla ölçülecektir.")
    lines.append("- **Eşleşmeyen işaretlerin niteliği:** Eşleşmeyen işaretlerin (`gemma4:12b-it-qat` için sayfa başına 1,92 adet) bir kısmı 3 modelli kurulun A taramasında işaretlemediği gerçek noktalama/yazım hataları veya stil önerileri olabilir; ancak bağımsız kurul oyu olmadığı için bu taramada tamamı muhafazakâr biçimde 'eşleşmeyen işaret' olarak sayılmıştır.")
    lines.append("- **Çalışma süresi:** `gemma4:12b-it-qat` ile sayfa okuma sayfa başına ortalama 15,21 sn (300 sayfalık kitap için ~76 dk) sürmektedir; bu nedenle ürüne eklenirken hızlı kural/morfoloji taramasından ayrı, isteğe bağlı veya arka plan (derin tarama) adımı olarak konumlandırılması uygundur.")
    lines.append("")

    rapor_yolu = PROJE / "testseti" / "k47_sonuclari.md"
    rapor_yolu.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rapor yazıldı: {rapor_yolu} ({len(lines)} satır)")


if __name__ == "__main__":
    main()
