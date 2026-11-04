@echo off
rem Yazim modeli gece egitimi (K33): Vikipedi ciftleri -> veri -> egitim -> olcum.
rem Yarida kalirsa yeniden cift tiklayin: biten adimlar atlanir, egitim kayit noktasindan devam eder.
rem Once: sarj aleti takili, oyunlar ve Ollama kapali, dizustu kapagi acik kalsin.
chcp 65001 >nul
cd /d "%~dp0"
set HF_HOME=%~dp0modeller\.hf
set TMP=D:\tmp_pip
set TEMP=D:\tmp_pip
set HF_HUB_DISABLE_TELEMETRY=1
tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul && echo UYARI: Ollama acik, ekran karti bellegini kullaniyor. Kapatmaniz onerilir.
".venv\Scripts\python.exe" -m derskitabi.yazim_modeli.gece %*
echo.
echo Bitti. Ozet: veri\yazim_modeli\gece.log
pause
