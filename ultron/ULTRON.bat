@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 > nul
title ULTRON
cd /d "%~dp0"

:: Sanal ortam
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [WARN] .venv bulunamadi. Kurulum icin scripts\install_windows.bat calistirin.
)

:: Kurulum yapılmış mı kontrol
if not exist "frontend\node_modules" (
    echo [HATA] Frontend kurulmamis. scripts\install_windows.bat calistirin.
    pause & exit /b 1
)

:: Backend logları için klasör
if not exist "logs" mkdir logs

:: Arka planda backend başlat
echo [1/3] Backend baslatiliyor (port 8000)...
start "ULTRON-BACKEND" /min cmd /c "title ULTRON-BACKEND && cd backend && python -B server.py 2>> ..\logs\backend.log"

:: Backend'in hazır olmasını bekle
echo [2/3] Backend hazir bekleniyor...
set /a tries=0
:wait_loop
timeout /t 1 /nobreak > nul
set /a tries+=1
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/config', timeout=1)" > nul 2>&1
if errorlevel 1 (
    if !tries! lss 15 goto wait_loop
    echo [WARN] Backend 15s icinde yanit vermedi - devam ediliyor...
) else (
    echo [OK]  Backend hazir ^(^!tries^! saniye^)
)

:: Frontend başlat
echo [3/3] Frontend baslatiliyor (port 5173)...
start "ULTRON-FRONTEND" /min cmd /c "title ULTRON-FRONTEND && cd frontend && npm run dev 2>> ..\logs\frontend.log"

:: Tarayıcıda aç
timeout /t 3 /nobreak > nul
start http://127.0.0.1:5173

echo.
echo  ULTRON ayakta.
echo  Desktop : http://127.0.0.1:5173
echo  Backend : http://127.0.0.1:8000
echo  Logs    : logs\ klasorune bakın
echo.
echo  Kapatmak icin bu pencereyi kapatin ve görev yoneticisinden
echo  ULTRON-BACKEND ve ULTRON-FRONTEND pencerelerini kapatın.
echo.
pause
