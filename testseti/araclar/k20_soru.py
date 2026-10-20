"""Bir blok soru/etkinlik içinde mi? (K20 test seti maddeleri için)"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASLIK = re.compile(r"DEĞERLENDİR|ÖRNEK SORU|\bSORULAR\b|ÖLÇME|TEMA SONU", re.I)
YONERGE = re.compile(r"soruları|cevaplayınız|eşleştiriniz|doğru ise|yanlış ise|işaretleyiniz|boşluklara|"
                     r"aşağıdakilerden hangisi", re.I)
NUMARALI = re.compile(r"^\s*[\"“(…]*\s*(\d+\s*[.)]|[a-eçA-E]\))")


def etkinlik_bloklari(bloklar):
    """{(sayfa, blok)}: değerlendirme sayfalarındaki tüm bloklar + yönergeden sonraki numaralı/soru blokları."""
    sonuc, sayfa = set(), {}
    for b in bloklar:
        sayfa.setdefault(b["sayfa_no"], []).append(b)
    for s, bs in sayfa.items():
        if any(BASLIK.search(b["metin"]) for b in bs[:3]):
            sonuc |= {(s, b["blok_no"]) for b in bs}
            continue
        for i, b in enumerate(bs):
            onceki = bs[max(0, i - 6):i]
            if NUMARALI.match(b["metin"]) or (any(YONERGE.search(x["metin"]) for x in onceki)
                                              and (NUMARALI.match(b["metin"]) or b["metin"].rstrip().endswith("?"))):
                sonuc.add((s, b["blok_no"]))
            if YONERGE.search(b["metin"]):
                sonuc.add((s, b["blok_no"]))
                # yönergenin hemen ardından gelen metin parçası ("aşağıdaki metne göre")
                if i + 1 < len(bs):
                    sonuc.add((s, bs[i + 1]["blok_no"]))
    return sonuc


if __name__ == "__main__":
    t = json.loads(Path(r"D:\derskitabı\testseti\tutarlilik_celiskileri.json").read_text(encoding="utf-8"))
    for kitap in ("kitap", "biyoloji10"):
        bl = json.loads(Path(rf"D:\derskitabı\veri\{kitap}_bloklar.json").read_text(encoding="utf-8"))
        eb = etkinlik_bloklari(bl)
        print(kitap, "etkinlik bloğu:", len(eb), "/", len(bl))
        for o in t:
            if o["kitap"] != kitap:
                continue
            yerler = [("kaynak", k["sayfa_no"], k["blok_no"]) for k in o["kaynaklar"]] + \
                     [("hedef", o["hedef"]["sayfa_no"], o["hedef"]["blok_no"])]
            kotu = [f"{ad} s{s}b{bn}" for ad, s, bn in yerler if (s, bn) in eb]
            if kotu:
                print(" ", o["id"], kotu)
