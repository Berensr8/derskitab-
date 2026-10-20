"""K23 yazım test setini üretir: gerçek paragraflara sabit tohumlu rastgele yazım hataları ekler.

Kelime hataları (kelime dışı hata: sonuç iki araca göre de geçersiz bir kelime olmalı):
  tr_karakter  Türkçe harf kaybı (ş→s, ğ→g, ı→i, ö→o, ü→u, ç→c)   "kişisel" → "kisisel"
  dusme        bir harf düşer                                    "fonksiyon" → "foksiyon"
  ikileme      bir harf iki kez yazılır                          "özellik" → "özellliklerini"
  yer_degisme  yan yana iki harf yer değiştirir                    "olacağını" → "olcaağını"
Kural hataları (TDK): noktalama_bosluk, bitisik_ayri, ya_da, bag_de_da_uyum, kelime_tekrari, bag_te_ta.

Her blokta en fazla bir değişiklik; yazım tespiti olan bloklar ve blok başı/sonu kelimeleri
kullanılmaz (sistemin bilerek atladığı yerler). Çıktı: testseti/yazim_hatalari.json

Kullanım: python testseti/araclar/k23_yazim_olustur.py
"""
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

PROJE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJE))
from derskitabi.kayit import bloklari_yukle  # noqa: E402
from derskitabi.kriterler import yazim  # noqa: E402
from derskitabi.kriterler.tutarlilik import konusma_mi  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
TOHUM = 20261020
KITAPLAR = {"kitap": "S", "biyoloji10": "B"}
KELIME_HATASI = {"tr_karakter": 7, "dusme": 7, "ikileme": 7, "yer_degisme": 7}  # kitap başına
KURAL_HATASI = {"noktalama_bosluk": 4, "bitisik_ayri": 3, "ya_da": 1, "bag_de_da_uyum": 2,
                "kelime_tekrari": 1, "bag_te_ta": 1}
GELISTIRME_ORANI = 0.3
TR = {"ş": "s", "ğ": "g", "ı": "i", "ö": "o", "ü": "u", "ç": "c"}
UNSUZ = set("bcçdfgğhjklmnprsştvyz")


def kelime_hatasi(kelime: str, tur: str, rnd: random.Random) -> str | None:
    ic = range(1, len(kelime) - 1)  # ilk ve son harfe dokunma (gerçekçi ve tanınabilir)
    if tur == "tr_karakter":
        yerler = [i for i, c in enumerate(kelime) if c in TR]
        if not yerler:
            return None
        i = rnd.choice(yerler)
        return kelime[:i] + TR[kelime[i]] + kelime[i + 1:]
    if tur == "dusme":
        i = rnd.choice(list(ic))
        return kelime[:i] + kelime[i + 1:]
    if tur == "ikileme":
        yerler = [i for i in ic if kelime[i] in UNSUZ]
        if not yerler:
            return None
        i = rnd.choice(yerler)
        return kelime[:i] + kelime[i] + kelime[i:]
    if tur == "yer_degisme":
        yerler = [i for i in range(1, len(kelime) - 2) if kelime[i] != kelime[i + 1]]
        if not yerler:
            return None
        i = rnd.choice(yerler)
        return kelime[:i] + kelime[i + 1] + kelime[i] + kelime[i + 2:]
    raise ValueError(tur)


# Kural hataları: (desen, değiştirme fonksiyonu, beklenen alt tür)
def kural_adaylari(metin: str, tur: str):
    """(eski, yeni, aranan parça) üçlüleri; eski blokta tam bir kez geçmeli."""
    if tur == "noktalama_bosluk":
        for m in re.finditer(r"([a-zçğıöşü]{3,}), ([a-zçğıöşü]{3,})", metin):
            yield m.group(0), f"{m.group(1)},{m.group(2)}", f"{m.group(1)},{m.group(2)}"
    elif tur == "bitisik_ayri":
        for dogru, yanlis in (("birçok", "bir çok"), ("hiçbir", "hiç bir"), ("herhangi", "her hangi"),
                              ("birkaç", "bir kaç")):
            for m in re.finditer(rf"(?<![\wçğıöşü]){dogru}(?![\wçğıöşü])", metin):
                bag = metin[max(0, m.start() - 12):m.end() + 12]
                yield bag, bag.replace(dogru, yanlis, 1), yanlis
    elif tur == "ya_da":
        for m in re.finditer(r"[a-zçğıöşü]{3,} ya da [a-zçğıöşü]{3,}", metin):
            yield m.group(0), m.group(0).replace(" ya da ", " yada ", 1), "yada"
    elif tur in ("bag_de_da_uyum", "bag_te_ta"):
        for m in re.finditer(r"([a-zçğıöşü]{3,}) (de|da) ([a-zçğıöşü]{3,})", metin):
            once, bag, sonra = m.groups()
            ou = yazim.son_unlu(once)
            beklenen = "da" if ou in yazim.KALIN_UNLULER else "de"
            if bag != beklenen:  # kitapta zaten uyumsuz: kullanma
                continue
            if tur == "bag_de_da_uyum":
                yeni_bag = "de" if bag == "da" else "da"
            elif bag == "de":
                yeni_bag = "te"
            else:
                continue  # "ta" yalnız noktalamadan önce hata sayılır (R3); "te" seçilir
            yield m.group(0), f"{once} {yeni_bag} {sonra}", f"{once} {yeni_bag}"
    elif tur == "kelime_tekrari":
        for m in re.finditer(r"[a-zçğıöşü]{3,} ve [a-zçğıöşü]{3,}", metin):
            yield m.group(0), m.group(0).replace(" ve ", " ve ve ", 1), "ve ve"


def main() -> None:
    rnd = random.Random(TOHUM)
    starlang, zemberek = yazim.varsayilan_denetciler()
    gecersiz = lambda k: not yazim._gecerli(starlang, k) and not yazim._gecerli(zemberek, k)  # noqa: E731
    cikti = []
    for kitap, harf in KITAPLAR.items():
        bloklar = bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")
        tespitli = {(t["sayfa_no"], t["blok_no"]) for t in
                    json.loads((PROJE / "veri" / f"{kitap}_yazim_tespitler.json").read_text(encoding="utf-8"))}
        kitap_kelimeleri = yazim.kitap_kelime_sayilari(bloklar)
        uygun = [b for b in bloklar if b.tur == "paragraf" and len(b.metin.split()) >= 15
                 and (b.sayfa_no, b.blok_no) not in tespitli and not konusma_mi(b.metin)
                 and not yazim._aralikli_mi(b.metin)]
        rnd.shuffle(uygun)
        kullanilan, ogeler = set(), []

        def ekle(b, tur, alt, eski, yeni, aranan, beklenen):
            ogeler.append({"kitap": kitap, "tur": tur, "alt_tur": alt, "beklenen_alt_tur": beklenen,
                           "aranan": aranan, "sayfa_no": b.sayfa_no, "blok_no": b.blok_no,
                           "hedef": {"sayfa_no": b.sayfa_no, "blok_no": b.blok_no, "islem": "degistir",
                                     "eski": eski, "yeni": yeni}})
            kullanilan.add((b.sayfa_no, b.blok_no))

        for alt, n in KELIME_HATASI.items():
            for b in uygun:
                if sum(o["alt_tur"] == alt for o in ogeler) >= n:
                    break
                if (b.sayfa_no, b.blok_no) in kullanilan:
                    continue
                kelimeler = list(re.finditer(r"(?<![\wçğıöşü'’])[a-zçğıöşü]{6,}(?![\wçğıöşü'’-])", b.metin))[1:-1]
                rnd.shuffle(kelimeler)
                for m in kelimeler:
                    k = m.group(0)
                    if not (yazim._gecerli(starlang, k) and yazim._gecerli(zemberek, k)):
                        continue
                    hatali = kelime_hatasi(k, alt, rnd)
                    if not hatali or not gecersiz(hatali) or kitap_kelimeleri[hatali] > 0:
                        continue
                    bag = b.metin[max(0, m.start() - 15):m.end() + 15]
                    if b.metin.count(bag) != 1:
                        continue
                    ekle(b, "kelime", alt, bag, bag.replace(k, hatali, 1), hatali, "morfoloji")
                    break
        for alt, n in KURAL_HATASI.items():
            beklenen = {"bag_te_ta": "bag_te_ta"}.get(alt, alt)
            for b in uygun:
                if sum(o["alt_tur"] == alt for o in ogeler) >= n:
                    break
                if (b.sayfa_no, b.blok_no) in kullanilan:
                    continue
                for eski, yeni_metin, aranan in kural_adaylari(b.metin, alt):
                    if b.metin.count(eski) == 1:
                        ekle(b, "kural", alt, eski, yeni_metin, aranan, beklenen)
                        break
        ogeler.sort(key=lambda o: (o["sayfa_no"], o["blok_no"]))
        for i, o in enumerate(ogeler, 1):
            o["id"] = f"Y{harf}{i:02d}"
        kimlikler = [o["id"] for o in ogeler]
        gelistirme = set(rnd.sample(kimlikler, round(len(kimlikler) * GELISTIRME_ORANI)))
        for o in ogeler:
            o["set"] = "gelistirme" if o["id"] in gelistirme else "test"
        print(kitap, len(ogeler), Counter(o["alt_tur"] for o in ogeler))
        cikti += ogeler
    (PROJE / "testseti" / "yazim_hatalari.json").write_text(
        json.dumps([{k: o[k] for k in ("id", "kitap", "set", "tur", "alt_tur", "beklenen_alt_tur", "aranan",
                                       "sayfa_no", "blok_no", "hedef")} for o in cikti],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("toplam", len(cikti), Counter(o["set"] for o in cikti))


if __name__ == "__main__":
    main()
