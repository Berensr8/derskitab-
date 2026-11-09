"""Seçili kitaplarda bugünkü sistemle (hakemsiz, varsayılan) yazım tespitleri: sayfa A için ve B örneklemi için."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from derskitabi.kayit import bloklari_yukle
from derskitabi.kriterler import yazim, dusuk_oncelik
CIKTI = Path(sys.argv[1])
for kitap in ["biyoloji9", "biyoloji11", "turkdili10", "turkdili11", "turkdili12"]:
    t0 = time.time()
    bloklar = bloklari_yukle(Path(f"veri/{kitap}_bloklar.json"))
    t = yazim.analiz_et(bloklar, kitap_bloklari=bloklar)
    t = dusuk_oncelik.isaretle(Path(f"veri/{kitap}.pdf"), bloklar, t)
    (CIKTI / f"{kitap}_sistem.json").write_text(json.dumps([x.__dict__ if not hasattr(x, 'sozluge') else x.sozluge() for x in t], ensure_ascii=False, default=list), encoding="utf-8")
    print(kitap, len(t), "tespit,", sum(x.guven_skoru >= 0.5 for x in t), "gösterilen,", round(time.time() - t0), "sn", flush=True)
