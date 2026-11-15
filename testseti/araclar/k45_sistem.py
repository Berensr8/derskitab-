"""K45 adım 1.3: ürünün varsayılan yapılandırmasıyla kilitli A ve B havuzu sayfalarında yazım tespitleri.

Hakemsiz: dusuk_oncelik.isaretle(pdf, bloklar, yazim.analiz_et(bloklar)) (sonuclar.py ile aynı zincir).
Hakemli (ürünün varsayılanı, Ollama + gemma4 hazırsa): aynı çıktıya yazım hakemi (hakemle) eklenir.
Çıktılar veri/bagimsiz3/ altına yazılır (git dışı).
"""
import json
import time
from pathlib import Path

from k45_ortak import CIKTI, KITAPLAR, PROJE, olcum_sayfalari, ortam_kontrol

bilgi = ortam_kontrol(sert=False)

from derskitabi.kayit import bloklari_yukle
from derskitabi.kriterler import dusuk_oncelik, yazim
from derskitabi.kriterler.yazim_hakem import hakem_varsayilani, hakemle

if not hakem_varsayilani():
    raise SystemExit("DUR: hakem varsayılanı kapalı (Ollama/gemma4 hazır değil). Önce OLLAMA_BASLAT.bat çalıştırın.")

CIKTI.mkdir(parents=True, exist_ok=True)
onbellek_yolu = PROJE / "veri" / "yazim_hakem_onbellek.json"  # ürünle aynı önbellek (sonuclar.py)
onbellek = json.loads(onbellek_yolu.read_text(encoding="utf-8")) if onbellek_yolu.exists() else {}
onbellek_bas = len(onbellek)


def yaz(yol: Path, tespitler) -> None:
    yol.write_text(json.dumps([t.sozluge() for t in tespitler], ensure_ascii=False, default=list), encoding="utf-8")


print("Kod:", bilgi, flush=True)
for kitap in KITAPLAR:
    t0 = time.time()
    bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
    hakemsiz = dusuk_oncelik.isaretle(PROJE / "veri" / f"{kitap}.pdf", bloklar, yazim.analiz_et(bloklar))
    sayfalar = olcum_sayfalari(kitap)
    secili = [t for t in hakemsiz if t.sayfa_no in sayfalar]
    yaz(CIKTI / f"{kitap}_sistem_hakemsiz.json", secili)
    print(f"{kitap}: kitapta {len(hakemsiz)} tespit; ölçüm sayfalarında {len(secili)}; hakemsiz bitti ({round(time.time() - t0)} sn)", flush=True)
    try:
        hakemli = hakemle(secili, bloklar, onbellek=onbellek, ilerleme=lambda m: print("  " + m, flush=True))
    finally:
        onbellek_yolu.write_text(json.dumps(onbellek, ensure_ascii=False), encoding="utf-8")
    yaz(CIKTI / f"{kitap}_sistem_hakemli.json", hakemli)
    print(f"{kitap}: hakemli bitti; gösterilen (güven>=0,5): hakemsiz {sum(t.guven_skoru >= 0.5 for t in secili)}, "
          f"hakemli {sum(t.guven_skoru >= 0.5 for t in hakemli)} ({round(time.time() - t0)} sn)", flush=True)
print(f"Hakem önbelleği: {onbellek_bas} -> {len(onbellek)} kayıt (yeni sorulan {len(onbellek) - onbellek_bas})")
