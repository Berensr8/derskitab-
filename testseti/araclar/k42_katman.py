"""K42 ön kayıt eki (K41-ek): metin katmanı mekanik kontrolü.

Bir adayın metni, PDF'in glif düzeyindeki karakterlerinden (page.get_texttrace()) farklıysa
aday "metin katmanı farkı" sayılır: ne gerçek hata ne de sistem isabeti; pay ve paydadan çıkarılır.
Kontrol kuraldır, kimse elle karar vermez: adayın her sözcüğü (boşluksuz, NFKC) sayfanın glif
metninde aranır; bulunmayan sözcük varsa aday işaretlenir. Satır sonu tiresi için tireler
atılarak bir kez daha denenir.
"""
import re
import unicodedata

_ATILAN = re.compile(r"[\s\xad\u200b\u200c\u200d\ufeff\x00-\x08]")


def _norm(s: str) -> str:
    return _ATILAN.sub("", unicodedata.normalize("NFKC", s))


def sayfa_glif_metni(sayfa) -> str:
    """Sayfanın glif düzeyindeki metni (get_texttrace; ActualText etiketine bakmaz)."""
    return _norm("".join(chr(c[0]) for iz in sayfa.get_texttrace() for c in iz["chars"]))


def katman_farki(glif_metni: str, parca: str) -> list[str]:
    """Adayda olup glif metninde bulunmayan sözcükler (boş liste = fark yok)."""
    tiresiz = glif_metni.replace("-", "")
    eksik = []
    for sozcuk in parca.split():
        s = _norm(sozcuk)
        if not s or s in glif_metni:
            continue
        if s.replace("-", "") in tiresiz:
            continue
        eksik.append(sozcuk)
    return eksik
