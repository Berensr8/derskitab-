"""Yerel dil modelleri (Ollama) ile konuşmak: tutarlılık (K17) ve yazım hakemi (K25) ortak kullanır.

  - Geçici hatalarda artan beklemeyle yeniden deneme (5xx her zaman geçici sayılır).
  - Model değişirken diğer modeller bellekten boşaltılır (8 GB ekran kartında tek model).
  - sohbet(): JSON şemasıyla zorlanmış cevap; "düşünme" ayarını desteklemeyen modellerde
    ayarsız yeniden dener.
Önce `ollama serve` (ya da OLLAMA_BASLAT.bat).
"""

import json
import re
import time
import urllib.error
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"

# Uzun çalıştırmalarda Ollama'nın model çalıştırıcısı ara sıra çöküp yeniden yükleniyor
# ("model runner has unexpectedly stopped" — Biyoloji 10 değerlendirmesinde görüldü). Böyle
# geçici hatalarda istek artan beklemeyle yeniden denenir; kalıcı hatalar hemen bildirilir.
YENIDEN_DENEME = (5, 20, 60)  # saniye
_GECICI = ("unexpectedly stopped", "connection", "forcibly closed", "timed out", "EOF", "terminated")


def istek(yol: str, govde: dict) -> dict:
    for bekleme in (*YENIDEN_DENEME, None):
        r = urllib.request.Request(OLLAMA_URL + yol, json.dumps(govde).encode("utf-8"),
                                   {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=300) as cevap:
                return json.loads(cevap.read())
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            mesaj = e.read().decode(errors="ignore") if isinstance(e, urllib.error.HTTPError) else str(e)
            # Sunucu hataları (5xx) geçicidir; mesaj metnine güvenilmez (Windows hatayı Türkçe
            # verebiliyor: "Varolan bir bağlantı … zorla kapatıldı"). 4xx (ör. model yok) kalıcıdır.
            gecici = (not isinstance(e, urllib.error.HTTPError) or e.code >= 500
                      or any(g in mesaj for g in _GECICI))
            if gecici and bekleme is not None:
                time.sleep(bekleme)
                continue
            if isinstance(e, urllib.error.HTTPError):
                raise RuntimeError(f"Ollama hatası ({govde.get('model')}): {mesaj}") from e
            raise RuntimeError("Ollama'ya bağlanılamadı. Önce `ollama serve` çalıştırın.") from e


def _istek_get(yol: str) -> dict:
    with urllib.request.urlopen(OLLAMA_URL + yol, timeout=30) as cevap:
        return json.loads(cevap.read())


def yuklu_modeller() -> set[str] | None:
    """Bilgisayarda kurulu modeller; Ollama çalışmıyorsa None."""
    try:
        return {m["name"] for m in _istek_get("/api/tags")["models"]}
    except (OSError, ValueError, KeyError):
        return None


_SON_MODEL: list[str | None] = [None]


def yalniz_bu_model(model: str) -> None:
    """Model değişirken bellekteki diğer modelleri boşaltır. 8 GB ekran kartında gemma4 (~8,5 GB)
    yüklüyken bge-m3 yüklenemeyip çalıştırıcı çöktü ("Load failed", 0xc0000409); her an tek
    model bulunsun."""
    if _SON_MODEL[0] == model:
        return
    try:
        yuklu = [m["name"] for m in _istek_get("/api/ps").get("models", [])]
    except (OSError, ValueError):  # sunucuya ulaşılamazsa boşaltmadan devam (asıl istek hatayı bildirir)
        yuklu = []
    for m in yuklu:
        if m != model and m.split(":latest")[0] != model:
            for yol, govde in (("/api/generate", {"model": m, "keep_alive": 0}),
                               ("/api/embed", {"model": m, "input": "", "keep_alive": 0})):
                try:
                    istek(yol, govde)
                    break
                except RuntimeError:
                    continue  # gömme modeli /api/generate'i desteklemez
    _SON_MODEL[0] = model


_DUSUNME_DESTEKLI: dict[str, bool] = {}


def sohbet(model: str, sistem: str, soru: str, ozellikler: dict, num_predict: int,
           num_ctx: int = 4096) -> dict | None:
    """JSON şemasıyla (ozellikler: {alan: json-şema}) cevap ister; çözülemezse None."""
    yalniz_bu_model(model)
    govde = {"model": model, "stream": False,
             "format": {"type": "object", "properties": ozellikler, "required": list(ozellikler)},
             "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict},
             "messages": [{"role": "system", "content": sistem}, {"role": "user", "content": soru}]}
    if _DUSUNME_DESTEKLI.get(model, True):
        try:
            cevap = istek("/api/chat", {**govde, "think": False})
        except RuntimeError as e:
            if "think" not in str(e):
                raise
            _DUSUNME_DESTEKLI[model] = False  # model "düşünme" ayarını desteklemiyor
            cevap = istek("/api/chat", govde)
    else:
        cevap = istek("/api/chat", govde)
    icerik = re.sub(r"<think>.*?</think>", "", cevap["message"]["content"], flags=re.S)
    try:
        return json.loads(icerik)
    except json.JSONDecodeError:
        return None
