@echo off
rem Sunum baslaticisi: cift tiklayin ya da bir PDF'i bu dosyanin uzerine surukleyin.
chcp 65001 >nul
cd /d "%~dp0"
".venv\Scripts\python.exe" -m derskitabi.demo %*
echo.
pause
