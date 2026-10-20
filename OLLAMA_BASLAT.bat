@echo off
rem Ollama sunucusunu bilgisayari zorlamayacak ayarlarla baslatir (2026-10-20 cokmesinden sonra).
rem  - Ekran karti belleginin 1 GB i bos birakilir: ekran surucusu sikismasin.
rem  - Ayni anda tek model ve tek istek.
rem Uzun islerden once bilgisayari sarja takin; Windows guc modunu "Dengeli" yapmaniz onerilir.
set OLLAMA_GPU_OVERHEAD=1073741824
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_NUM_PARALLEL=1
ollama serve
