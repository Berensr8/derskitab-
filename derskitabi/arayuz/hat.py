"""İnceleme hattı: arayüzün başlattığı ayrı süreç (demo.py ile aynı adımlar, soru sormadan).

Ayarlar <çıktı>/ayar.json'dan okunur. İlerleme <çıktı>/ilerleme.jsonl'e satır satır yazılır
(arayüz bunu okur), bitince sonuç ekranının içeriği <çıktı>/ozet.json'a yazılır.
Ayrı süreç olmasının sebebi: vazgeçilince süreç durdurulabilir, bir çökme arayüzü etkilemez.

    python -m derskitabi.arayuz.hat <çıktı klasörü>
"""

import json
import sys
import time
import traceback
from pathlib import Path

ADIMLAR = [("pdf", "PDF'ten metni okuma"), ("okunabilirlik", "Dilsel karmaşıklık"),
           ("yazim", "Yazım denetimi"), ("mufredat", "Öğretim programıyla karşılaştırma"),
           ("tutarlilik", "Kitap içi çelişkiler"), ("inceleme", "Sayfa sayfa inceleme dosyası"),
           ("dosyalar", "Notlu PDF ve Excel raporu")]


class Ilerleme:
    def __init__(self, klasor: Path):
        self.yol = klasor / "ilerleme.jsonl"
        self.yol.write_text("", encoding="utf-8")

    def yaz(self, **kayit) -> None:
        kayit["zaman"] = time.time()
        with open(self.yol, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")

    def adim(self, kod: str, durum: str = "başladı", mesaj: str = "") -> None:
        self.yaz(adim=kod, durum=durum, mesaj=mesaj)

    def mesaj(self, kod: str, mesaj: str) -> None:
        self.yaz(adim=kod, durum="mesaj", mesaj=mesaj)


def ollama_durumu() -> str | None:
    """Yerel modeller hazır mı? Değilse sebebi (kullanıcıya gösterilecek cümle)."""
    from .. import yerel_model
    from ..kriterler import tutarlilik
    modeller = yerel_model.yuklu_modeller()
    if modeller is None:
        return "Yerel model programı (Ollama) çalışmıyor. OLLAMA_BASLAT.bat ile başlatılabilir."
    eksik = [m for m in (tutarlilik.GOMME_MODELI, tutarlilik.HAKEM_MODELI, tutarlilik.IKINCI_GORUS_MODELI)
             if m not in modeller and m + ":latest" not in modeller]
    return f"Gereken yerel model yüklü değil: {', '.join(eksik)}." if eksik else None


def calistir(klasor: Path) -> dict:
    import pymupdf

    from ..inceleyici import inceleme_html_olustur
    from ..kayit import bloklari_kaydet, json_kaydet, tespitleri_kaydet, tespitleri_yukle
    from ..kriterler import dusuk_oncelik, mufredat, okunabilirlik, tutarlilik, yazim, yazim_hakem
    from ..pdf_cikarma import bloklari_cikar
    from ..pdf_notlari import notlu_pdf_olustur
    from ..rapor import rapor_olustur
    from ..sonuclar import KitapSonuclari
    from .ozet import kriter_ozeti

    ayar = json.loads((klasor / "ayar.json").read_text(encoding="utf-8"))
    pdf = Path(ayar["pdf"])
    secilen = set(ayar["kriterler"])
    il = Ilerleme(klasor)
    baslangic = time.time()
    proje = Path(__file__).resolve().parents[2]

    il.adim("pdf")
    with pymupdf.open(pdf) as belge:
        sayfa_sayisi = len(belge)
    bloklar = bloklari_cikar(pdf)
    bloklari_kaydet(bloklar, klasor / "bloklar.json")
    sayfalar = ayar.get("sayfalar")  # None = bütün kitap
    secili = set(sayfalar) if sayfalar else None
    sec = (lambda liste: [x for x in liste if x.sayfa_no in secili]) if secili else (lambda liste: liste)
    il.adim("pdf", "bitti", f"{sayfa_sayisi} sayfa, {len(bloklar)} metin bloğu")

    # Okunabilirlik kitabın tamamına göre hesaplanır ("en zor %10" kitap geneline göre); hedef sınıf da buradan
    il.adim("okunabilirlik")
    try:
        ozet, okun = okunabilirlik.analiz_et(bloklar, ayar.get("sinif"))
        json_kaydet(ozet.sozluge(), klasor / "okunabilirlik_ozet.json")
        tespitleri_kaydet(okun, klasor / "okunabilirlik_tespitler.json")
    except ValueError:
        ozet, okun = None, []
    hedef = ayar.get("sinif") or (ozet.hedef_sinif if ozet else None)
    il.adim("okunabilirlik", "bitti" if "okunabilirlik" in secilen else "atlandı",
            f"{len(sec(okun))} zor paragraf" if "okunabilirlik" in secilen else "Seçilmedi.")

    neden = {}
    yazim_t = None
    if "yazim" in secilen:
        il.adim("yazim")
        yazim_t = yazim.analiz_et([b for b in bloklar if secili is None or b.sayfa_no in secili],
                                  kitap_bloklari=bloklar)
        yazim_t = dusuk_oncelik.isaretle(pdf, bloklar, yazim_t)
        if ayar.get("yazim_hakemi"):
            sebep = ollama_durumu()
            if sebep:
                il.mesaj("yazim", f"Yapay zekâ hakemi atlandı: {sebep}")
            else:
                il.mesaj("yazim", "Şüpheli kelimeler yapay zekâ hakemine soruluyor…")
                onbellek_yolu = proje / "veri" / "yazim_hakem_onbellek.json"
                onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
                try:
                    yazim_t = yazim_hakem.hakemle(yazim_t, bloklar, onbellek=onbellek,
                                                  ilerleme=lambda m: il.mesaj("yazim", m))
                finally:
                    json_kaydet(onbellek, onbellek_yolu)
        tespitleri_kaydet(yazim_t, klasor / "yazim_tespitler.json")
        il.adim("yazim", "bitti", f"{sum(t.guven_skoru >= 0.5 for t in yazim_t)} olası hata")
    else:
        il.adim("yazim", "atlandı", "Seçilmedi.")

    muf_t = None
    if "mufredat" in secilen:
        il.adim("mufredat")
        bulunan = mufredat.program_bul(bloklar, hedef)
        if bulunan is None:
            neden["mufredat"] = ("Bu kitaba uyan öğretim programı bulunamadı (şimdilik Biyoloji, Türk Dili ve "
                                 "Edebiyatı, Sosyal Bilgiler programları yüklü).")
            il.adim("mufredat", "atlandı", neden["mufredat"])
        else:
            yol, sinif, ciktilar = bulunan
            muf_t = mufredat.kavram_kontrolu(bloklar, ciktilar)
            tespitleri_kaydet(muf_t, klasor / "mufredat_tespitler.json")
            ders = {"biyoloji": "Biyoloji", "sosyal": "Sosyal Bilgiler", "turkdili": "Türk Dili ve Edebiyatı"}.get(
                yol.stem.replace("_programi", ""), yol.stem)
            il.adim("mufredat", "bitti", f"{ders} {sinif}. sınıf programı: {len(muf_t)} not")
    else:
        il.adim("mufredat", "atlandı", "Seçilmedi.")

    tut_kayit = tut_t = None
    if "tutarlilik" in secilen:
        il.adim("tutarlilik")
        hazir = pdf.with_name(pdf.stem + "_tutarlilik_adaylar.json")
        hazir_t = pdf.with_name(pdf.stem + "_tutarlilik_tespitler.json")
        if hazir.exists() and hazir_t.exists():
            tut_kayit = json.loads(hazir.read_text(encoding="utf-8"))
            tut_t = tutarlilik.dogru_yanlis_suz(tespitleri_yukle(hazir_t), bloklar)
            il.mesaj("tutarlilik", "Bu kitap için önceden hesaplanmış sonuç kullanıldı.")
        elif sebep := ollama_durumu():
            neden["tutarlilik"] = sebep
        else:
            onbellek_yolu = klasor / "tutarlilik_onbellek.json"
            onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
            tut_kayit = []
            try:
                tut_t = tutarlilik.analiz_et([b for b in bloklar if secili is None or b.sayfa_no in secili],
                                             kayit=tut_kayit, onbellek=onbellek,
                                             ilerleme=lambda m: il.mesaj("tutarlilik", m),
                                             haric=tutarlilik.alinti_haric(bloklar, pdf))
            finally:
                json_kaydet(onbellek, onbellek_yolu)
            tespitleri_kaydet(tut_t, klasor / "tutarlilik_tespitler.json")
            json_kaydet(tut_kayit, klasor / "tutarlilik_adaylar.json")
        il.adim("tutarlilik", "atlandı" if tut_t is None else "bitti",
                neden.get("tutarlilik") or f"{len(sec(tut_t))} olası çelişki")
    else:
        il.adim("tutarlilik", "atlandı", "Seçilmedi.")

    il.adim("inceleme")
    inceleme_html_olustur(pdf, klasor / "inceleme.html", sayfalar, bloklar=bloklar, analiz=(ozet, okun),
                          yazim_tespitleri=yazim_t or [], tutarlilik_kaydi=tut_kayit,
                          mufredat_tespitleri=muf_t, mufredat_oku=False)
    il.adim("inceleme", "bitti")

    il.adim("dosyalar")
    okun_sec = sec(okun) if "okunabilirlik" in secilen else []
    sonuclar = KitapSonuclari(bloklar, {
        "yazim": sec(yazim_t or []), "okunabilirlik": okun_sec,
        "tutarlilik": sec(tut_t) if tut_t is not None else None, "mufredat": muf_t}, ozet, tut_kayit)
    kapsam = f"Yalnız seçili {len(sayfalar)} sayfa incelendi." if sayfalar else None
    notlu = klasor / f"{pdf.stem}_notlu.pdf"
    notlu_pdf_olustur(pdf, notlu, bloklar=bloklar, yazim_tespitleri=sonuclar.tespitler["yazim"],
                      okunabilirlik_tespitleri=okun_sec, tutarlilik_tespitleri=sonuclar.tespitler["tutarlilik"],
                      tutarlilik_kaydi=tut_kayit, kapsam=kapsam, mufredat_tespitleri=muf_t)
    excel = klasor / f"{pdf.stem}_rapor.xlsx"
    rapor_olustur(excel, sonuclar, pdf.name, sayfa_sayisi, kapsam)
    il.adim("dosyalar", "bitti")

    blok_sozluk = {(b.sayfa_no, b.blok_no): b for b in bloklar}
    kriterler, no = {}, 1
    for kod, tespitler, ek in (
            ("yazim", sec(yazim_t) if yazim_t is not None else None, {}),
            ("okunabilirlik", okun_sec if "okunabilirlik" in secilen else None,
             {"okunabilirlik_ozeti": ozet.sozluge() if ozet else None}),
            ("mufredat", muf_t, {}),
            ("tutarlilik", sec(tut_t) if tut_t is not None else None, {})):
        if tespitler is None and kod not in secilen:
            continue  # seçilmeyen kriter sonuç ekranında hiç görünmez
        kriterler[kod] = kriter_ozeti(kod, tespitler, blok_sozluk, no, neden=neden.get(kod), **ek)
        no += len(kriterler[kod]["maddeler"])
    sonuc = {
        "kitap": {"ad": ayar.get("kitap_adi") or pdf.stem, "dosya": pdf.name, "sayfa_sayisi": sayfa_sayisi,
                  "sinif": hedef, "kapsam": ayar.get("sayfa_metni") or "Bütün kitap"},
        "sure_sn": round(time.time() - baslangic),
        "kriterler": kriterler,
        "ciktilar": {"inceleme": "inceleme.html", "notlu_pdf": notlu.name, "excel": excel.name},
    }
    json_kaydet(sonuc, klasor / "ozet.json")
    il.yaz(durum="tamam", sure_sn=sonuc["sure_sn"])
    return sonuc


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    klasor = Path(sys.argv[1])
    try:
        calistir(klasor)
    except Exception as hata:  # noqa: BLE001 — kullanıcıya gösterilir, ayrıntı günlükte
        with open(klasor / "ilerleme.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"durum": "hata", "mesaj": f"{type(hata).__name__}: {hata}", "zaman": time.time()},
                               ensure_ascii=False) + "\n")
        (klasor / "hata.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
