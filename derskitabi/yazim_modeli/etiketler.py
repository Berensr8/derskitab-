"""Sınıflar (kelime başına bir etiket) ve GECTurk kurallarının bu sınıflara eşlenmesi."""

SINIFLAR = ["DOGRU", "HARF", "BITISIK_AYRI", "BUYUK_KUCUK", "KURAL_DIGER"]
SINIF_NO = {s: i for i, s in enumerate(SINIFLAR)}
ACIKLAMA = {
    "HARF": "harf hatası ya da yanlış kelime biçimi",
    "BITISIK_AYRI": "bitişik / ayrı yazım (de/da, ki, ya da, birleşik kelimeler)",
    "BUYUK_KUCUK": "büyük / küçük harf",
    "KURAL_DIGER": "yazım kuralı (kesme işareti, kısaltma, de/da uyumu…)",
}

# GECTurk kural numarası → sınıf (Kara vd. 2023, Tablo 1)
GECTURK_KURALLARI = {
    1: "BITISIK_AYRI",   # CONJ_DE_SEP: bağlaç de/da ayrı yazılır (oğlunada)
    2: "KURAL_DIGER",    # CONJ_DE_VH: bağlaç de/da ünlü uyumu (çok de)
    3: "KURAL_DIGER",    # CONJ_DE_AR: bağlaç de/da ünsüz benzeşmesi yok (sınıf ta)
    4: "BITISIK_AYRI",   # YADA: ya da ayrı (yada)
    5: "KURAL_DIGER",    # CONJ_DE_APOS: bağlaç de/da kesmeyle yazılmaz (Ayşe'de)
    6: "BITISIK_AYRI",   # CASE_DE: hâl eki -de bitişik (Ev de)
    7: "BITISIK_AYRI",   # CONJ_KI_SEP: bağlaç ki ayrı (yorulmuşki)
    8: "BITISIK_AYRI",   # CONJ_KI_EXC: belki, sanki… bitişik (Bel ki)
    9: "HARF",           # FOREIGN_R1: gram → gıram
    10: "KURAL_DIGER",   # tabloda yok (makalede 25 kural): genel kural sınıfı
    11: "KURAL_DIGER",
    12: "HARF",          # PRONOUNC_EXC: başlıyacağım
    13: "HARF",          # BISYLL_HAPL_VOW: ağızı
    14: "HARF",          # BISYLL_HAPL_VOW_EXC: içerde
    15: "HARF",          # FOREIGN_R2: sebepi
    16: "HARF",          # FOREIGN_R2_EXC: evrağı
    17: "BITISIK_AYRI",  # LIGHT_VERB_SEP: arzetmek
    18: "BITISIK_AYRI",  # LIGHT_VERB_ADJ: emir etti
    19: "KURAL_DIGER",
    20: "BITISIK_AYRI",  # COMP_VERB_ADJ: uyuya kalmak
    21: "KURAL_DIGER",
    22: "BITISIK_AYRI",  # PRONOUN_EXC: hiç bir
    23: "BUYUK_KUCUK",   # SENT_CAP: cümle başı küçük
    24: "HARF",          # CAPPED: kağıt (şapka)
    25: "KURAL_DIGER",   # ABBREV: kısaltma ekleri
}


def gecturk_sinifi(kural: int) -> int:
    """GECTurk etiketi (0 = hatasız) → bizim sınıf numaramız."""
    return 0 if kural == 0 else SINIF_NO[GECTURK_KURALLARI.get(kural, "KURAL_DIGER")]
