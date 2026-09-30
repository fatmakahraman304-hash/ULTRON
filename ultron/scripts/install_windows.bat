@echo off
chcp 65001 > nul
setlocal EnableExtensions EnableDelayedExpansion
title ULTRON — Kurulum

echo.
echo  ██╗   ██╗██╗  ████████╗██████╗  ██████╗ ███╗   ██╗
echo  ██║   ██║██║  ╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║
echo  ██║   ██║██║     ██║   ██████╔╝██║   ██║██╔██╗ ██║
echo  ██║   ██║██║     ██║   ██╔══██╗██║   ██║██║╚██╗██║
echo  ╚██████╔╝███████╗██║   ██║  ██║╚██████╔╝██║ ╚████║
echo   ╚═════╝ ╚══════╝╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
echo  Jarvis-class AI — Windows Kurulum v19
echo.

:: ── Kök dizin
cd /d "%~dp0.."
set "ROOT=%CD%"

:: ── Ön koşul: Python
where python > nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi!
    echo        https://python.org/downloads adresinden Python 3.11+ kurun.
    echo        Kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
    pause & exit /b 1
)
python -c "import sys; exit(0 if sys.version_info>=(3,11) else 1)" 2>nul
if errorlevel 1 (
    echo [HATA] Python 3.11+ gerekli. Mevcut surum eski.
    pause & exit /b 1
)
echo [OK] Python bulundu.

:: ── Ön koşul: Node.js
where node > nul 2>&1
if errorlevel 1 (
    echo [HATA] Node.js bulunamadi!
    echo        https://nodejs.org adresinden LTS surum kurun.
    pause & exit /b 1
)
echo [OK] Node.js bulundu.

:: ── 1. Sanal ortam
echo.
echo [1/6] Python sanal ortami...
if not exist ".venv\Scripts\activate.bat" (
    python -m venv .venv
    if errorlevel 1 ( echo [HATA] venv olusturulamadi. & pause & exit /b 1 )
    echo       Sanal ortam olusturuldu.
) else (
    echo       Mevcut sanal ortam kullaniliyor.
)
call .venv\Scripts\activate.bat

:: ── 2. Pip yükseltme
echo.
echo [2/6] pip guncelleniyor...
python -m pip install --upgrade pip --quiet

:: ── 3. Python bağımlılıkları
echo.
echo [3/6] Python bagimliliklari kuruluyor...
python -m pip install -r backend\requirements.txt --quiet
if errorlevel 1 ( echo [HATA] requirements.txt kurulumu basarisiz. & pause & exit /b 1 )
python -m pip install -r backend\requirements.v16.txt --quiet
if errorlevel 1 ( echo [WARN] requirements.v16.txt kismen basarisiz - opsiyonel moduller eksik kalabilir. )
echo [OK] Python bagimliliklari hazir.

:: ── 4. Frontend bağımlılıkları
echo.
echo [4/6] Frontend bagimliliklari kuruluyor...
cd "%ROOT%\frontend"
if exist "package-lock.json" (
    call npm ci --silent
    if errorlevel 1 ( echo [WARN] npm ci basarisiz, npm install deneniyor... & call npm install --silent )
) else (
    call npm install --silent
)
echo [OK] Desktop frontend hazir.

if exist "%ROOT%\frontend-mobile\package.json" (
    cd "%ROOT%\frontend-mobile"
    if exist "package-lock.json" (
        call npm ci --silent 2>nul || call npm install --silent
    ) else (
        call npm install --silent
    )
    echo [OK] Mobile frontend hazir.
)
cd "%ROOT%"

:: ── 5. Ollama kontrol
echo.
echo [5/6] Ollama kontrolu...
where ollama > nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama bulunamadi.
    echo        1. https://ollama.com adresinden Ollama'yi kurun
    echo        2. Kurulumdan sonra cmd'de su komutu calistirin:
    echo           ollama pull qwen2.5-coder:7b
    echo           ollama pull llava:7b
) else (
    echo [OK] Ollama mevcut.
    ollama list 2>nul | findstr /i "qwen" > nul
    if errorlevel 1 (
        echo       qwen2.5-coder:7b indiriliyor (bu birkaç dakika alabilir)...
        start /wait ollama pull qwen2.5-coder:7b
    )
    ollama list 2>nul | findstr /i "llava" > nul
    if errorlevel 1 (
        echo       llava:7b indiriliyor (bu birkaç dakika alabilir)...
        start /wait ollama pull llava:7b
    )
    echo [OK] Ollama modelleri hazir.
)

:: ── 6. Kurulum sonrası
echo.
echo [6/6] Sistem muhürleniyor ve saglik taramasi yapiliyor...
cd "%ROOT%\backend"
python -B -c "
from app.personal.user_dna import MasterRules
r = MasterRules()
print('   master_rules.json muhürlendi.')
" 2>nul

python -B -c "
from app.core.doctor import run_doctor
r = run_doctor({'db_paths':[], 'rules_path':'config/security/master_rules.json'})
print('   DOCTOR:', r['overall'])
print('  ', r['summary'])
" 2>nul

cd "%ROOT%"

echo.
echo [DOGRULAMA] Bagimliliklar kontrol ediliyor...
python scripts\check_deps.py
echo.
echo ════════════════════════════════════════════════
echo   Kurulum tamamlandi!
echo   Baslatmak icin: cift tiklayin ULTRON.bat
echo ════════════════════════════════════════════════
echo.
pause
