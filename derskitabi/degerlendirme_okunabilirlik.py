"""Değerlendirme: okunabilirlik kriterini paragrafların geldiği sınıf düzeyiyle ölçer (K24).

Okunabilirlik için elle etiketlenmiş "doğru cevap" yok; bilinen tek nesnel bilgi paragrafın
hangi sınıfın kitabından geldiği. Üç ölçüm:
  1. Kitap düzeyi : 4 kitabın genel puanı (ortanca) sınıf sırasını izliyor mu?
  2. Ayırt etme   : üst sınıf kitabından rastgele bir paragrafın 6. sınıf kitabından rastgele bir
                    paragraftan "daha zor" çıkma olasılığı (AUC; 0,5 = yazı tura, 1,0 = kusursuz).
  3. Ekleme testi : 6. sınıf kitabına üst sınıf kitaplarından paragraflar eklenir; sistemin
                    bunları "en zor %10" içinde işaretleme oranı, kitabın kendi paragraflarınınkiyle
                    karşılaştırılır. Eklenen paragrafların listesi kilitlidir.

Kullanım:
    python -m derskitabi.degerlendirme_okunabilirlik
"""

import json
import random
import statistics
import sys

from .degerlendirme import PROJE, set_yukle
from .kayit import bloklari_yukle, json_kaydet
from .kriterler import okunabilirlik
from .model import Blok

KITAPLAR = {"kitap": 6, "turkdili9": 9, "biyoloji10": 10, "matematik11": 11}
TABAN = "kitap"
EKLEME_KAYNAKLARI = {"biyoloji10": 30, "turkdili9": 30}
EKLEME_YOLU = PROJE / "testseti" / "okunabilirlik_eklemeleri.json"
EKLEME_SHA256 = "38a141fb4e1167752edb7d9c197f1f886b0b1f98ed1ba7929c98406613f5d56e"  # K24
TOHUM = 20261020
FORMULLER = {"atesman": True, "cetinkaya_uzun": True, "bezirci_yilmaz": False}  # True: düşük puan = zor
# Aynı dersin farklı sınıf kitapları (MEB OGM, 2026-10-20 indirildi). Not: 9-10 Biyoloji ve 9 TDE
# yeni programın "Tema" düzeninde, 11 Biyoloji ve 10-11 TDE "Ünite" düzeninde (eski program).
DERS_SERILERI = {"Biyoloji": {"biyoloji9": 9, "biyoloji10": 10, "biyoloji11": 11},
                 "Türk Dili ve Edebiyatı": {"turkdili9": 9, "turkdili10": 10, "turkdili11": 11}}


def _bloklar(kitap: str) -> list[Blok]:
    return bloklari_yukle(PROJE / "veri" / f"{kitap}_bloklar.json")


def aday_paragraflar(bloklar: list[Blok]) -> list[tuple[Blok, okunabilirlik.Skorlar]]:
    """Sistemin değerlendirdiği paragraflar (≥ MIN_CUMLE cümle)."""
    return [(b, s) for b in bloklar if b.tur == "paragraf" and (s := okunabilirlik.skorla(b.metin))
            and s.cumle_sayisi >= okunabilirlik.MIN_CUMLE]


def auc(zor: list[float], kolay: list[float], dusuk_zor: bool) -> float:
    """P(zor gruptan rastgele paragraf, kolay gruptan rastgele paragraftan daha zor) — eşitlik yarım."""
    toplam = 0.0
    for x in zor:
        for y in kolay:
            if x == y:
                toplam += 0.5
            elif (x < y) == dusuk_zor:
                toplam += 1
    return toplam / (len(zor) * len(kolay))


def eklemeleri_olustur() -> list[dict]:
    rnd = random.Random(TOHUM)
    secilen = []
    for kitap, n in EKLEME_KAYNAKLARI.items():
        adaylar = aday_paragraflar(_bloklar(kitap))
        for b, _ in rnd.sample(adaylar, n):
            secilen.append({"kaynak_kitap": kitap, "sinif": KITAPLAR[kitap], "sayfa_no": b.sayfa_no,
                            "blok_no": b.blok_no, "metin": b.metin})
    return secilen


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rapor = {"kitap_duzeyi": {}, "auc": {}, "ekleme": {}}

    # 1. Kitap düzeyi
    print("1. Kitap düzeyi (ortanca puanlar):")
    paragraflar = {}
    for kitap, sinif in KITAPLAR.items():
        bloklar = _bloklar(kitap)
        ozet, tespitler = okunabilirlik.analiz_et(bloklar)
        paragraflar[kitap] = aday_paragraflar(bloklar)
        rapor["kitap_duzeyi"][kitap] = {"sinif": sinif, "atesman": ozet.atesman, "cetinkaya_uzun": ozet.cetinkaya_uzun,
                                        "bezirci_yilmaz": ozet.bezirci_yilmaz, "bezirci_duzeyi": ozet.bezirci_yilmaz_duzeyi,
                                        "isaretlenen": len(tespitler), "aday": len(paragraflar[kitap])}
        print(f"  {sinif:>2}. sınıf {kitap:12} Ateşman {ozet.atesman:5}  Çetinkaya-Uzun {ozet.cetinkaya_uzun:5}  "
              f"Bezirci-Yılmaz {ozet.bezirci_yilmaz:5} ({ozet.bezirci_yilmaz_duzeyi})")

    # 2. Ayırt etme gücü: her üst sınıf kitabı 6. sınıf kitabına karşı
    print("\n2. Ayırt etme gücü (AUC, 6. sınıf kitabına karşı):")
    for kitap in KITAPLAR:
        if kitap == TABAN:
            continue
        rapor["auc"][kitap] = {f: round(auc([getattr(s, f) for _, s in paragraflar[kitap]],
                                            [getattr(s, f) for _, s in paragraflar[TABAN]], dusuk), 3)
                               for f, dusuk in FORMULLER.items()}
        print(f"  {KITAPLAR[kitap]:>2}. sınıf {kitap:12}", rapor["auc"][kitap])

    # 3. Ekleme testi (kilitli liste)
    if not EKLEME_YOLU.exists():
        json_kaydet(eklemeleri_olustur(), EKLEME_YOLU)
        print(f"\n(Eklenecek paragraflar seçildi ve kaydedildi: {EKLEME_YOLU.name})")
    eklemeler = set_yukle(EKLEME_YOLU, kilit=EKLEME_SHA256)
    taban = _bloklar(TABAN)
    eklenen = [Blok(9999, 10000 + i, (0, 0, 1, 1), e["metin"], None, "paragraf") for i, e in enumerate(eklemeler)]
    _, tespitler = okunabilirlik.analiz_et(taban + eklenen, hedef_sinif=6)
    isaretli = {(t.sayfa_no, t.blok_no) for t in tespitler}
    yerli = [b for b, _ in paragraflar[TABAN]]
    yerli_oran = sum((b.sayfa_no, b.blok_no) in isaretli for b in yerli) / len(yerli)
    print(f"\n3. Ekleme testi: 6. sınıf kitabına {len(eklenen)} üst sınıf paragrafı eklendi.")
    print(f"  Kitabın kendi paragrafları: %{yerli_oran * 100:.1f} işaretlendi ({len(yerli)} paragraf)")
    rapor["ekleme"]["yerli_oran"] = round(yerli_oran, 3)
    for kitap in EKLEME_KAYNAKLARI:
        grup = [b for b, e in zip(eklenen, eklemeler) if e["kaynak_kitap"] == kitap]
        oran = sum((b.sayfa_no, b.blok_no) in isaretli for b in grup) / len(grup)
        rapor["ekleme"][kitap] = round(oran, 3)
        print(f"  {KITAPLAR[kitap]}. sınıf ({kitap}) paragrafları: %{oran * 100:.1f} işaretlendi ({len(grup)} paragraf)")
    # 4. Ders içi: aynı dersin farklı sınıf kitapları (ders farkı sınıf farkına karışmasın)
    print("\n4. Ders içi karşılaştırma (aynı ders, farklı sınıf):")
    rapor["ders_ici"] = {}
    for ders, kitaplar in DERS_SERILERI.items():
        mevcut = {k: s for k, s in kitaplar.items() if (PROJE / "veri" / f"{k}_bloklar.json").exists()}
        if len(mevcut) < 2:
            continue
        p = {k: aday_paragraflar(_bloklar(k)) for k in mevcut}
        ortanca = {k: {f: round(statistics.median(getattr(s, f) for _, s in p[k]), 1) for f in FORMULLER}
                   for k in mevcut}
        sirali = sorted(mevcut, key=mevcut.get)
        aucler = {f"{b}>{a}": {f: round(auc([getattr(s, f) for _, s in p[b]], [getattr(s, f) for _, s in p[a]], dusuk), 3)
                              for f, dusuk in FORMULLER.items()}
                  for i, a in enumerate(sirali) for b in sirali[i + 1:]}
        rapor["ders_ici"][ders] = {"ortanca": ortanca, "auc": aucler}
        print(f"  {ders}:")
        for k in sirali:
            print(f"    {mevcut[k]:>2}. sınıf {k:12} ({len(p[k])} paragraf) ortanca {ortanca[k]}")
        for cift, d in aucler.items():
            print(f"    AUC {cift}: {d}")
    json_kaydet(rapor, PROJE / "veri" / "degerlendirme_okunabilirlik.json")


if __name__ == "__main__":
    main()
