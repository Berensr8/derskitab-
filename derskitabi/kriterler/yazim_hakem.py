"""Yazım hakemi (K25, F3): kelime denetiminin tespitlerini yerel dil modeline danışır.

Morfoloji araçları (Starlang, Zemberek) bilmedikleri her kelimeyi hata sayar: bilimsel terimler,
eski yazımlı alıntılar (İstiklal Marşı, divan şiiri), araçların sözlüğünde olmayan doğru
kelimeler ("ithafen", "gluten"). K23 ölçümünde tespitlerin yalnız %6–30'u gerçek hataydı.
Hakem, her kelime tespitini cümlesiyle birlikte gemma4'e sorar:
  - "dogru"   → tespit silinmez; güveni 0,25'e iner, "muhtemelen doğru" notu eklenir
                (editör hiçbir şeyi kaybetmez, ama önce gerçek hatalara bakar);
  - "hata"    → güven korunur (yalnız bir araç demişse 0,5 → 0,75), önerilen yazım eklenir;
  - "belirsiz"/cevap yok → tespit olduğu gibi kalır.
TDK kural tespitlerine dokunulmaz (K23'te 9'un 8'i isabetliydi).
"""

import json
from collections.abc import Callable
from dataclasses import replace

from .. import yerel_model
from ..donanim import Bekci
from ..model import Blok, Tespit
from . import yazim
from .alinti import ALINTI_NOTU
from .okunabilirlik import cumlelere_bol

HAKEM_MODELI = "gemma4:12b-it-qat"
DUSUK_GUVEN = 0.25
KARARLAR = ("hata", "dogru", "belirsiz")
_HARFLER = "abcçdefgğhıijklmnoöprsştuüvyzâîû"
_TR_ESI = {"s": "ş", "ş": "s", "i": "ı", "ı": "i", "g": "ğ", "ğ": "g", "o": "ö", "ö": "o",
           "u": "ü", "ü": "u", "c": "ç", "ç": "c"}


def _yazim_hatasi_komsulari(kelime: str) -> set[str]:
    """Gerçekçi tek yazım hatasıyla bu kelimeye dönüşebilecek kelimeler (ters yönde):
    bir harf eksik kalmış (ekleme), bir harf fazla yazılmış (son harf hariç silme), Türkçe harf
    yerine Latin harfi ya da tersi, yan yana iki harf yer değiştirmiş. Rastgele harf değişimi ve
    son harfin silinmesi alınmaz: geliştirme verisinde bunlar terimleri geçerli kelimelere
    benzetiyordu ("tüzlük"→"düzlük", "grid"→"gri", "nelerin"→"neleri")."""
    k = yazim.tr_kucuk(kelime)
    sonuc = {k[:i] + h + k[i:] for i in range(len(k) + 1) for h in _HARFLER}
    sonuc |= {k[:i] + k[i + 1:] for i in range(len(k) - 1)}
    sonuc |= {k[:i] + _TR_ESI[c] + k[i + 1:] for i, c in enumerate(k) if c in _TR_ESI}
    sonuc |= {k[:i] + k[i + 1] + k[i] + k[i + 2:] for i in range(len(k) - 1)}
    sonuc.discard(k)
    return sonuc


def yakin_dogru_kelime(kelime: str, kitap_kelimeleri, denetciler) -> str | None:
    """Kitapta geçen ve iki araca göre de geçerli, tek yazım hatası uzaklığında bir kelime.
    Dil modeli küçük yazım hatalarının üzerinden okuyabiliyor ("jandama"yı "jandarma" sanıp
    doğru dedi); bu durumda tespit düşük önceliğe indirilmez (K25 düzeltmesi)."""
    adaylar = sorted((k for k in _yazim_hatasi_komsulari(kelime) if kitap_kelimeleri[k] >= 1),
                     key=lambda k: -kitap_kelimeleri[k])
    return next((k for k in adaylar if all(yazim._gecerli(d, k) for d in denetciler)), None)

SISTEM = """Sen Türkçe ders kitapları için çalışan bir yazım editörüsün. Bir yazım denetleyicisi aşağıdaki kelimeyi sözlüğünde bulamadı. Görevin: kelimenin bu cümlede doğru yazılıp yazılmadığına karar vermek.
- "dogru": Türkçede doğru yazılmış bir kelime ya da çekimi; bilimsel veya teknik terim; birim; özel isim; yabancı ya da Latince ad; şiir, tarihî metin veya konuşma aktarımı gibi alıntılardaki özgün/eski yazım (şapkalı harfler, eski imla, ağız özellikleri, Azerbaycan Türkçesi vb.); kısaltma.
- "hata": yazım yanlışı — harf eksik, fazla ya da yer değiştirmiş; Türkçe harf yerine Latin harfi (ş→s, ı→i); kelimenin doğrusu açıkça belli.
- "belirsiz": emin değilsin (ör. PDF'ten bozuk okunmuş bir parça olabilir).
Hata ise "oneri" alanına doğru yazımı yaz, değilse boş bırak. Önce kısa bir Türkçe açıklama yaz (en fazla iki cümle), sonra kararını ver."""

# (kelime, cümle, önceki cümle) -> {"karar", "aciklama", "oneri"}
Hakem = Callable[[str, str, str], dict]


def ollama_yazim_hakemi(kelime: str, cumle: str, onceki: str) -> dict:
    soru = f"Kelime: {kelime}\nCümle: {cumle}" + (f"\nÖnceki cümle: {onceki}" if onceki else "")
    j = yerel_model.sohbet(HAKEM_MODELI, SISTEM, soru,
                           {"aciklama": {"type": "string"}, "karar": {"type": "string", "enum": list(KARARLAR)},
                            "oneri": {"type": "string"}}, num_predict=200, num_ctx=2048)
    if j is None or j.get("karar") not in KARARLAR:
        return {"karar": "belirsiz", "aciklama": "", "oneri": ""}
    return {"karar": j["karar"], "aciklama": j.get("aciklama", ""), "oneri": j.get("oneri", "")}


def baglam(blok_metni: str, kelime: str) -> tuple[str, str]:
    """Kelimenin geçtiği cümle ve bir önceki cümle (cümle bulunamazsa blok metninden bir kesit)."""
    cumleler = cumlelere_bol(blok_metni)
    for i, c in enumerate(cumleler):
        if kelime in c:
            return c[:400], (cumleler[i - 1][:300] if i else "")
    yer = max(0, blok_metni.find(kelime))
    return blok_metni[max(0, yer - 150):yer + len(kelime) + 150], ""


def hakemle(tespitler: list[Tespit], bloklar: list[Blok], hakem: Hakem | None = None,
            onbellek: dict | None = None, ilerleme: Callable[[str], None] | None = None,
            bekci: Bekci | None = None, kitap_bloklari: list[Blok] | None = None,
            denetciler=None) -> list[Tespit]:
    """Kelime tespitlerini hakeme danışıp güvenlerini ayarlar; yeni liste döner (girdi değişmez).
    kitap_bloklari: yakın kelime kontrolü için kitabın tamamı (verilmezse bloklar)."""
    if hakem is None:
        hakem = ollama_yazim_hakemi
        bekci = bekci or Bekci(ilerleme or print)
    onbellek = {} if onbellek is None else onbellek
    yaz = ilerleme or (lambda _m: None)
    metin = {(b.sayfa_no, b.blok_no): b.metin for b in bloklar}
    kitap_kelimeleri = yazim.kitap_kelime_sayilari(kitap_bloklari or bloklar)
    denetciler = denetciler or yazim.varsayilan_denetciler()
    sonuc, soruldu, dusen = [], 0, 0
    for t in tespitler:
        if t.alt_tur != "morfoloji" or not t.metin_parcasi or ALINTI_NOTU in t.aciklama:
            sonuc.append(t)  # alıntı (K28): model eski yazımı "düzeltmeye" kalkmasın, düşük öncelikte kalır
            continue
        cumle, onceki = baglam(metin.get((t.sayfa_no, t.blok_no), ""), t.metin_parcasi)
        anahtar = json.dumps([HAKEM_MODELI, t.metin_parcasi, cumle, onceki], ensure_ascii=False)
        if anahtar not in onbellek:
            if bekci:
                bekci.adim()
            try:
                onbellek[anahtar] = hakem(t.metin_parcasi, cumle, onceki)
            except RuntimeError as e:  # model cevap veremedi: tespit olduğu gibi kalır (önbelleğe yazılmaz)
                yaz(f"  ⚠ Hakem '{t.metin_parcasi}' için cevap veremedi: {str(e)[:80]}")
                sonuc.append(t)
                continue
            soruldu += 1
            if soruldu % 50 == 0:
                yaz(f"  hakem {soruldu} kelime")
        k = onbellek[anahtar]
        gerekce = f" Gerekçe: {k['aciklama']}" if k.get("aciklama") else ""
        yakin = (yakin_dogru_kelime(t.metin_parcasi, kitap_kelimeleri, denetciler)
                 if k["karar"] == "dogru" else None)
        if yakin:
            sonuc.append(replace(t, guven_skoru=0.5, aciklama=t.aciklama +
                                 f" Dil modeli (gemma4) doğru dedi, ama kelime kitapta geçen '{yakin}' kelimesine "
                                 f"tek harf uzaklıkta: olası yazım hatası.{gerekce}"))
        elif k["karar"] == "dogru":
            dusen += 1
            sonuc.append(replace(t, guven_skoru=DUSUK_GUVEN, aciklama=t.aciklama +
                                 f" Dil modeli (gemma4): muhtemelen doğru yazılmış (terim, özel isim, alıntı ya da "
                                 f"araçların bilmediği bir kelime) — düşük öncelik.{gerekce}"))
        elif k["karar"] == "hata":
            oneri = f" Önerilen yazım: '{k['oneri']}'." if k.get("oneri") else ""
            sonuc.append(replace(t, guven_skoru=max(t.guven_skoru, 0.75), aciklama=t.aciklama +
                                 f" Dil modeli (gemma4) de yazım hatası dedi.{oneri}{gerekce}"))
        else:
            sonuc.append(replace(t, aciklama=t.aciklama + " Dil modeli (gemma4) karar veremedi."))
    yaz(f"Yazım hakemi: {sum(t.alt_tur == 'morfoloji' for t in tespitler)} kelime tespiti, "
        f"{dusen} tanesi 'muhtemelen doğru' bulunup düşük önceliğe indi")
    return sonuc
