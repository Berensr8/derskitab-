"""K49 adım: ürünün varsayılan hattıyla (yazım → kitap ipuçları → yazım hakemi → sayfa okuma) iki yeni kitabın
bütün sayfalarında yazım tespitleri (ön kayıt: testseti/k49_on_kayit.md, ölçülen kod 68a7a71).

Zincir arayuz/hat.py ile aynıdır. Sayfa okuma uzun sürdüğü için önce sayfalar 20'lik parçalar hâlinde okutulup
önbellek her parçadan sonra diske yazılır (çökmede kaybolmasın); ardından ürünün `uygula` çağrısı bütün kitap
için bir kez, önbellekten çalıştırılır. Bu, tek çağrıyla birebir aynı çıktıyı verir (her sayfanın adayları yalnız
o sayfanın metnine ve o sayfadaki mevcut tespitlere bağlıdır).

Çıktılar veri/bagimsiz4/ altına (git dışı):
  <kitap>_sistem.json  : son hâl (sayfa okuma dahil; sayfa okumasız hâl alt_tur != 'sayfa_okuma' ile elde edilir)
  <kitap>_sayac.json   : sayfa okuma süzgeç sayaçları ve süreler
"""
import json
import time

from k49_ortak import CIKTI, KITAP_AD, KITAPLAR, PROJE, ortam_kontrol

bilgi = ortam_kontrol(sert=False)

from derskitabi.kayit import bloklari_yukle
from derskitabi.kriterler import dusuk_oncelik, sayfa_okuma, yazim
from derskitabi.kriterler.yazim_hakem import hakem_varsayilani, hakemle

if not hakem_varsayilani() or not sayfa_okuma.sayfa_okuma_varsayilani():
    raise SystemExit("DUR: hakem/sayfa okuma varsayılanı kapalı (Ollama/gemma4 hazır değil).")

CIKTI.mkdir(parents=True, exist_ok=True)
hakem_yolu = PROJE / "veri" / "yazim_hakem_onbellek.json"  # ürünle aynı önbellekler
okuma_yolu = PROJE / "veri" / sayfa_okuma.ONBELLEK_ADI
PARCA = 20


def yaz(yol, tespitler) -> None:
    yol.write_text(json.dumps([t.sozluge() for t in tespitler], ensure_ascii=False, default=list), encoding="utf-8")


def log(m: str) -> None:
    print(time.strftime("%H:%M:%S"), m, flush=True)


log(f"Kod: {bilgi}")
for kitap in KITAPLAR:
    t0 = time.time()
    pdf = PROJE / "veri" / f"{kitap}.pdf"
    bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")

    tespit = dusuk_oncelik.isaretle(pdf, bloklar, yazim.analiz_et(bloklar, kitap_bloklari=bloklar))
    log(f"{kitap}: yazım + ipuçları {len(tespit)} tespit ({round(time.time() - t0)} sn)")

    hakem_onbellek = json.loads(hakem_yolu.read_text(encoding="utf-8")) if hakem_yolu.exists() else {}
    try:
        tespit = hakemle(tespit, bloklar, onbellek=hakem_onbellek, ilerleme=lambda m: log("  " + m))
    finally:
        hakem_yolu.write_text(json.dumps(hakem_onbellek, ensure_ascii=False), encoding="utf-8")
    t_hakem = round(time.time() - t0)
    log(f"{kitap}: hakem bitti; gösterilen {sum(t.guven_skoru >= 0.5 for t in tespit)} ({t_hakem} sn)")

    alintilar = sayfa_okuma.alintilari_bul(pdf, bloklar, None)
    okuma_onbellek = sayfa_okuma.onbellek_yukle(okuma_yolu)
    sayfalar = sorted({b.sayfa_no for b in bloklar})
    for i in range(0, len(sayfalar), PARCA):  # önbelleği ısıt, her parçadan sonra kaydet
        parca = set(sayfalar[i:i + PARCA])
        try:
            sayfa_okuma.uygula(tespit, bloklar, sayfalar=parca, alintilar=alintilar, onbellek=okuma_onbellek,
                               kitap_adi=KITAP_AD[kitap])
        finally:
            sayfa_okuma.onbellek_kaydet(okuma_onbellek, okuma_yolu)
        log(f"  {kitap}: sayfa okuma {min(i + PARCA, len(sayfalar))}/{len(sayfalar)} sayfa "
            f"({round(time.time() - t0)} sn)")

    son, sayac = sayfa_okuma.uygula(tespit, bloklar, sayfalar=None, alintilar=alintilar, onbellek=okuma_onbellek,
                                    ilerleme=lambda m: log("  " + m), kitap_adi=KITAP_AD[kitap])
    yaz(CIKTI / f"{kitap}_sistem.json", son)
    so = [t for t in son if t.alt_tur == "sayfa_okuma"]
    (CIKTI / f"{kitap}_sayac.json").write_text(json.dumps(
        {"sayac": dict(sayac), "sure_sn": round(time.time() - t0), "hakem_sure_sn": t_hakem, "kod": bilgi},
        ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"{kitap}: bitti; toplam {len(son)} tespit, gösterilen {sum(t.guven_skoru >= 0.5 for t in son)} "
        f"(sayfa okuma gösterilen {sum(t.guven_skoru >= 0.5 for t in so)}); {round(time.time() - t0)} sn")
