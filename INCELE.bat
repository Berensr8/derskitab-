@echo off
rem Ders Kitabi Inceleme: cift tiklayin, program tarayicida acilir.
rem Bu pencere acik kaldikca program calisir.
chcp 65001 >nul
cd /d "%~dp0"
title Ders Kitabi Inceleme
".venv\Scripts\python.exe" -m derskitabi.arayuz.sunucu %*
if errorlevel 1 pause
