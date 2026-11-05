"""Arayüz sunucusu: bilgisayarda çalışır, tarayıcıda açılır (yalnız bu bilgisayardan erişilir: 127.0.0.1).

Yalnız Python'un kendi kütüphanesiyle yazıldı (yeni kurulum gerekmez). INCELE.bat ile başlar.

    python -m derskitabi.arayuz.sunucu [--port 8770] [--acma]
"""

import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import gecmis

PROJE = Path(__file__).resolve().parents[2]
SAYFA = Path(__file__).with_name("sayfa.html")
VARSAYILAN_PORT = 8770
SUREC: dict[str, subprocess.Popen] = {}
_PENCERE = threading.Lock()  # aynı anda tek dosya penceresi


# --- yardımcılar ---------------------------------------------------------------------------------

def pdf_bilgisi(pdf: str) -> dict:
    """Sayfa sayısı ve kapaktaki sınıf (ilk sayfalardaki "9. SINIF" gibi ifadeden), PDF'in kendi başlığı."""
    import pymupdf

    from ..kriterler.okunabilirlik import _HEDEF_SINIF, HEDEF_SINIF_ARAMA_SAYFASI
    yol = Path(pdf)
    if not yol.is_file() or yol.suffix.lower() != ".pdf":
        raise ValueError("Bu bir PDF dosyası değil.")
    with pymupdf.open(yol) as belge:
        sayfa = len(belge)
        sinif = None
        for i in range(min(HEDEF_SINIF_ARAMA_SAYFASI, sayfa)):
            m = _HEDEF_SINIF.search(belge[i].get_text())
            if m and 1 <= int(m.group(1)) <= 12:
                sinif = int(m.group(1))
                break
        baslik = (belge.metadata or {}).get("title") or ""
    ad = baslik.strip() if 3 < len(baslik.strip()) < 80 else yol.stem
    return {"pdf": str(yol), "dosya": yol.name, "ad": ad, "sayfa_sayisi": sayfa, "sinif": sinif,
            "cikti": str(gecmis.VARSAYILAN_CIKTI)}


def pencere(tur: str, baslangic: str | None = None) -> str | None:
    """Windows'un kendi dosya/klasör seçme penceresi (sunucu bilgisayarda çalıştığı için açılabilir)."""
    import tkinter
    from tkinter import filedialog
    with _PENCERE:
        kok = tkinter.Tk()
        kok.withdraw()
        kok.attributes("-topmost", True)
        try:
            if tur == "pdf":
                yol = filedialog.askopenfilename(title="İncelenecek ders kitabını seçin", initialdir=baslangic,
                                                 filetypes=[("PDF dosyaları", "*.pdf")])
            else:
                yol = filedialog.askdirectory(title="Sonuçlar nereye kaydedilsin?", initialdir=baslangic)
        finally:
            kok.destroy()
    return str(Path(yol)) if yol else None


def _klasor_adi(ad: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', " ", ad).strip()[:60] + time.strftime(" %Y-%m-%d %H.%M")


def ilerlemeyi_oku(klasor: Path) -> list[dict]:
    yol = klasor / "ilerleme.jsonl"
    if not yol.exists():
        return []
    satirlar = []
    for s in yol.read_text(encoding="utf-8").splitlines():
        try:
            satirlar.append(json.loads(s))
        except ValueError:
            pass  # yazılmakta olan son satır
    return satirlar


def inceleme_durumu(kayit: dict) -> dict:
    """Kaydın güncel hâli: ilerleme satırları, bittiyse özet; durum güncellenir."""
    klasor = Path(kayit["cikti"])
    ilerleme = ilerlemeyi_oku(klasor)
    son = next((s for s in reversed(ilerleme) if s.get("durum") in ("tamam", "hata")), None)
    surec = SUREC.get(kayit["id"])
    calisiyor = surec is not None and surec.poll() is None
    eski = kayit["durum"]
    if son and son["durum"] == "tamam":
        kayit["durum"] = "bitti"
    elif son and son["durum"] == "hata":
        kayit["durum"] = "hata"
        kayit["hata"] = son.get("mesaj")
    elif eski == "sürüyor" and not calisiyor:
        kayit["durum"] = "yarıda kaldı"
    ozet = None
    if kayit["durum"] == "bitti" and (klasor / "ozet.json").exists():
        ozet = json.loads((klasor / "ozet.json").read_text(encoding="utf-8"))
        kayit["ozet_sayilari"] = {k: v.get("sayilar") for k, v in ozet["kriterler"].items()}
        kayit["sure_sn"] = ozet.get("sure_sn")
    if kayit["durum"] != eski:
        kayit["bitis"] = kayit.get("bitis") or time.time()
        gecmis.kaydet(kayit)
    from .hat import ADIMLAR
    return {"kayit": kayit, "ilerleme": ilerleme, "ozet": ozet, "adimlar": ADIMLAR}


def baslat(istek: dict) -> dict:
    bilgi = pdf_bilgisi(istek["pdf"])
    kriterler = [k for k in istek.get("kriterler", []) if k in ("yazim", "okunabilirlik", "mufredat", "tutarlilik")]
    if not kriterler:
        raise ValueError("En az bir kriter seçin.")
    sayfalar = None
    if istek.get("sayfa_metni"):
        from ..gorsellestir import sayfa_araligi_coz
        sayfalar = sayfa_araligi_coz(istek["sayfa_metni"], bilgi["sayfa_sayisi"])
    ust = Path(istek.get("cikti") or gecmis.VARSAYILAN_CIKTI)
    klasor = ust / _klasor_adi(istek.get("kitap_adi") or bilgi["ad"])
    klasor.mkdir(parents=True, exist_ok=False)
    ayar = {"pdf": bilgi["pdf"], "kitap_adi": istek.get("kitap_adi") or bilgi["ad"], "kriterler": kriterler,
            "sayfalar": sayfalar, "sayfa_metni": f"Sayfa {istek['sayfa_metni']}" if sayfalar else None,
            "sinif": istek.get("sinif") or None, "yazim_hakemi": bool(istek.get("yazim_hakemi")), "cikti": str(klasor)}
    (klasor / "ayar.json").write_text(json.dumps(ayar, ensure_ascii=False, indent=1), encoding="utf-8")
    kayit = gecmis.yeni(ayar)
    gunluk = open(klasor / "gunluk.txt", "w", encoding="utf-8")
    surec = subprocess.Popen([sys.executable, "-m", "derskitabi.arayuz.hat", str(klasor)], cwd=PROJE,
                             stdout=gunluk, stderr=subprocess.STDOUT,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    SUREC[kayit["id"]] = surec
    kayit["pid"] = surec.pid
    gecmis.kaydet(kayit)
    return kayit


def vazgec(kimlik: str) -> None:
    surec = SUREC.get(kimlik)
    if surec and surec.poll() is None:
        surec.terminate()
        surec.wait(10)
    kayit = gecmis.oku(kimlik)
    if kayit and kayit["durum"] == "sürüyor":
        kayit.update(durum="vazgeçildi", bitis=time.time())
        gecmis.kaydet(kayit)


def ac(kimlik: str, ne: str) -> None:
    kayit = gecmis.oku(kimlik)
    if not kayit:
        raise ValueError("İnceleme bulunamadı.")
    klasor = Path(kayit["cikti"])
    hedef = klasor if ne == "klasor" else klasor / {
        "notlu_pdf": f"{Path(kayit['pdf']).stem}_notlu.pdf", "excel": f"{Path(kayit['pdf']).stem}_rapor.xlsx"}[ne]
    if not hedef.exists():
        raise ValueError("Dosya bulunamadı (klasör taşınmış ya da silinmiş olabilir).")
    os.startfile(hedef)  # noqa: S606 — kullanıcının kendi bilgisayarında, kendi dosyası


def durum_bilgisi() -> dict:
    from .hat import ollama_durumu
    return {"ollama": ollama_durumu(), "varsayilan_cikti": str(gecmis.VARSAYILAN_CIKTI)}


# --- HTTP ----------------------------------------------------------------------------------------

class Isleyici(BaseHTTPRequestHandler):
    def log_message(self, *_):  # konsolu kirletmesin
        pass

    def _gonder(self, kod: int, govde: bytes, tur: str) -> None:
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def _json(self, veri, kod: int = 200) -> None:
        self._gonder(kod, json.dumps(veri, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _istek(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _yerel_mi(self) -> bool:
        """Başka bir sitenin tarayıcı üzerinden bu sunucuya istek atmasını engeller."""
        kaynak = self.headers.get("Origin") or self.headers.get("Referer") or ""
        return not kaynak or urlparse(kaynak).hostname in ("127.0.0.1", "localhost")

    def do_GET(self):
        yol = urlparse(self.path).path
        try:
            if yol == "/":
                return self._gonder(200, SAYFA.read_bytes(), "text/html; charset=utf-8")
            if yol == "/api/durum":
                return self._json(durum_bilgisi())
            if yol == "/api/gecmis":
                return self._json([inceleme_durumu(k)["kayit"] if k["durum"] == "sürüyor" else k
                                   for k in gecmis.listele()])
            if m := re.fullmatch(r"/api/inceleme/([\w-]+)", yol):
                kayit = gecmis.oku(m.group(1))
                return self._json(inceleme_durumu(kayit) if kayit else {"hata": "Bulunamadı."}, 200 if kayit else 404)
            if m := re.fullmatch(r"/cikti/([\w-]+)/([^/]+)", yol):
                kayit = gecmis.oku(m.group(1))
                dosya = Path(kayit["cikti"]) / unquote(m.group(2)) if kayit else None
                if not dosya or not dosya.is_file() or dosya.parent != Path(kayit["cikti"]):
                    return self._json({"hata": "Bulunamadı."}, 404)
                tur = mimetypes.guess_type(dosya.name)[0] or "application/octet-stream"
                return self._gonder(200, dosya.read_bytes(), tur + ("; charset=utf-8" if tur.startswith("text") else ""))
            self._json({"hata": "Bulunamadı."}, 404)
        except Exception as hata:  # noqa: BLE001
            self._json({"hata": str(hata)}, 500)

    def do_POST(self):
        if not self._yerel_mi():
            return self._json({"hata": "İzin yok."}, 403)
        yol = urlparse(self.path).path
        try:
            istek = self._istek()
            if yol == "/api/sec/pdf":
                secilen = pencere("pdf", istek.get("baslangic"))
                return self._json(pdf_bilgisi(secilen) if secilen else {})
            if yol == "/api/sec/klasor":
                return self._json({"klasor": pencere("klasor", istek.get("baslangic"))})
            if yol == "/api/pdf-bilgisi":
                return self._json(pdf_bilgisi(istek["pdf"]))
            if yol == "/api/incele":
                return self._json(baslat(istek))
            if m := re.fullmatch(r"/api/inceleme/([\w-]+)/vazgec", yol):
                vazgec(m.group(1))
                return self._json({"tamam": True})
            if m := re.fullmatch(r"/api/inceleme/([\w-]+)/sil", yol):
                gecmis.sil(m.group(1))
                return self._json({"tamam": True})
            if m := re.fullmatch(r"/api/inceleme/([\w-]+)/ac", yol):
                ac(m.group(1), istek["ne"])
                return self._json({"tamam": True})
            self._json({"hata": "Bulunamadı."}, 404)
        except (ValueError, KeyError, FileExistsError) as hata:
            self._json({"hata": str(hata)}, 400)
        except Exception as hata:  # noqa: BLE001
            self._json({"hata": f"{type(hata).__name__}: {hata}"}, 500)


def zaten_acik(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/durum", timeout=2) as y:
            return y.status == 200
    except OSError:
        return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Ders kitabı inceleme arayüzü")
    ap.add_argument("--port", type=int, default=VARSAYILAN_PORT)
    ap.add_argument("--acma", action="store_true", help="Tarayıcıyı açma")
    arg = ap.parse_args()
    adres = f"http://127.0.0.1:{arg.port}/"
    if zaten_acik(arg.port):
        print(f"Program zaten açık: {adres}")
        if not arg.acma:
            webbrowser.open(adres)
        return
    sunucu = ThreadingHTTPServer(("127.0.0.1", arg.port), Isleyici)
    print(f"Ders Kitabı İnceleme açıldı: {adres}")
    print("Bu pencere açık kaldıkça program çalışır. Kapatmak için pencereyi kapatın.")
    if not arg.acma:
        threading.Timer(0.5, webbrowser.open, args=(adres,)).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
