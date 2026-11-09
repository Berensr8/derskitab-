"""Bağımsız değerlendirme paketi: A (sayfa okuma, sistemden bağımsız) ve B (sistem tespitlerini kör değerlendirme)."""
import json, random, sys
from pathlib import Path
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from derskitabi.yazim_modeli.veri import test_sayfalari

S = Path(sys.argv[1])
HEDEF = Path("bagimsiz_degerlendirme")
HEDEF.mkdir(exist_ok=True)
AD = {"biyoloji9": "Biyoloji 9", "biyoloji11": "Biyoloji 11", "turkdili10": "Türk Dili ve Edebiyatı 10",
      "turkdili11": "Türk Dili ve Edebiyatı 11", "turkdili12": "Türk Dili ve Edebiyatı 12"}
r0 = random.Random(20261109)
_haric0 = test_sayfalari()
A = []
for kitap in ["biyoloji9", "biyoloji11", "turkdili10"]:
    bl = json.load(open(f"veri/{kitap}_bloklar.json", encoding="utf-8"))
    say = {}
    for x in bl:
        if x["tur"] == "paragraf":
            say[x["sayfa_no"]] = say.get(x["sayfa_no"], 0) + len(x["metin"].split())
    son = max(x["sayfa_no"] for x in bl)
    uygun = sorted(s for s, n in say.items() if n >= 150 and s not in _haric0.get(kitap, set()) and 10 < s < son - 10)
    A += [(kitap, s) for s in sorted(r0.sample(uygun, 10))]
A = [(k, s, f"S{i:02d}") for i, (k, s) in enumerate(A, 1)]

# --- A: 30 sayfa tek PDF; her sayfanın üstüne kod damgası (sistemin çıktısı hiç gösterilmez)
birlesik = pymupdf.open()
metin = []
for kitap, s, kod in A:
    with pymupdf.open(f"veri/{kitap}.pdf") as d:
        birlesik.insert_pdf(d, from_page=s - 1, to_page=s - 1)
        metin.append(f"===== {kod} | {AD[kitap]}, PDF s.{s} =====\n" + d[s - 1].get_text())
    sf = birlesik[-1]
    kisa = {"biyoloji9": "Biyoloji 9", "biyoloji11": "Biyoloji 11", "turkdili10": "TDE 10"}[kitap]
    sf.insert_text((20, 18), f"{kod}  |  {kisa}, PDF s.{s}", fontsize=11, color=(0.64, 0.14, 0.1), fontname="helv")
birlesik.save(HEDEF / "A_30_sayfa.pdf", garbage=3, deflate=True)
(HEDEF / "A_30_sayfa_metin.txt").write_text("\n\n".join(metin), encoding="utf-8")
json.dump([{"kod": k, "kitap": a, "sayfa_no": s} for a, s, k in A], open(HEDEF / "A_sayfa_listesi.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# --- B: gösterilen (güven >= 0,5) tespitlerden kitap başına 8, daha önce etiketlenmemiş sayfalardan
haric = test_sayfalari()
for kitap, s, _ in A:
    haric.setdefault(kitap, set()).update({s - 1, s, s + 1})
r = random.Random(20261109)
secilen = []
for kitap in AD:
    bloklar = {(b["sayfa_no"], b["blok_no"]): b for b in json.load(open(f"veri/{kitap}_bloklar.json", encoding="utf-8"))}
    t = json.load(open(S / f"{kitap}_sistem.json", encoding="utf-8"))
    aday = [x for x in t if x["guven_skoru"] >= 0.5 and x["sayfa_no"] not in haric.get(kitap, set())]
    for x in r.sample(aday, 8):
        b = bloklar.get((x["sayfa_no"], x["blok_no"]), {"metin": ""})
        m = " ".join(b["metin"].split())
        i = m.find(x["metin_parcasi"])
        bas, son = (max(0, i - 110), min(len(m), i + len(x["metin_parcasi"]) + 110)) if i >= 0 else (0, 240)
        secilen.append({"kitap": kitap, "sayfa_no": x["sayfa_no"], "basili": x["basili_sayfa_no"],
                        "parca": x["metin_parcasi"], "baglam": ("…" if bas else "") + m[bas:son] + ("…" if son < len(m) else ""),
                        "gizli": {"alt_tur": x["alt_tur"], "guven": x["guven_skoru"], "aciklama": x["aciklama"]}})
r.shuffle(secilen)
for n, x in enumerate(secilen, 1):
    x["no"] = f"B{n:02d}"
json.dump(secilen, open(S / "B_anahtar.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# B listesi (yapay zekâlara verilecek düz metin; sistemin türü/güveni yok)
satirlar = [f"{x['no']} | {AD[x['kitap']]}, PDF s.{x['sayfa_no']} | İşaretlenen: «{x['parca']}» | Bağlam: {x['baglam']}"
            for x in secilen]
(HEDEF / "B_liste.txt").write_text("\n".join(satirlar) + "\n", encoding="utf-8")

# B Excel (Beren dolduracak)
wb = Workbook(); ws = wb.active; ws.title = "B - Tespitler"
bas = ["No", "Kitap", "PDF sayfa", "Basılı sayfa", "İşaretlenen", "Bağlam", "Kararın", "Notun (isteğe bağlı)"]
ws.append(bas)
for c in ws[1]:
    c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="E8E2D4")
for x in secilen:
    ws.append([x["no"], AD[x["kitap"]], x["sayfa_no"], x["basili"] or "", x["parca"], x["baglam"], "", ""])
dv = DataValidation(type="list", formula1='"Hata,Hata değil,Emin değilim"', allow_blank=True)
ws.add_data_validation(dv); dv.add(f"G2:G{len(secilen) + 1}")
for col, w in zip("ABCDEFGH", (6, 24, 10, 11, 22, 90, 15, 30)):
    ws.column_dimensions[col].width = w
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    row[6].fill = PatternFill("solid", fgColor="FFF4C2")
ws.freeze_panes = "A2"
wb.save(HEDEF / "B_benim_kararlarim.xlsx")

# A için sistemin bulduklarını gizli sakla (sonra karşılaştırılacak)
gizli = []
for kitap, s, kod in A:
    t = json.load(open(S / f"{kitap}_sistem.json", encoding="utf-8"))
    gizli += [{"sayfa": kod, **x} for x in t if x["sayfa_no"] == s]
json.dump(gizli, open(S / "A_sistem_gizli.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("B:", len(secilen), Counter(x["gizli"]["alt_tur"] for x in secilen))
print("A sayfalar:", [(k, s) for k, s, _ in A]); print("A sistem (gizli):", len(gizli), "tespit,", sum(g["guven_skoru"] >= 0.5 for g in gizli), "gösterilen")
