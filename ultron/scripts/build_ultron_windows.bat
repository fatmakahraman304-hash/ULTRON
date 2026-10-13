@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
title GÖLGE Windows Build

echo [1/4] Desktop frontend build ediliyor...
cd frontend
call npm install
if errorlevel 1 goto :error
call npm run build
if errorlevel 1 goto :error
cd ..

echo [2/4] Desktop paketleme bagimliliklari kuruluyor...
cd desktop
call npm install
if errorlevel 1 goto :error

echo [3/4] GÖLGE Windows installer uretiliyor...
call npm run dist
if errorlevel 1 goto :error
cd ..

echo [4/4] TAMAMLANDI.
echo Installer: desktop\dist\GOLGE-Setup-1.0.2.exe
echo.
echo Not: GÖLGE local Python + Ollama ortamini kullanir; herhangi bir bulut API anahtari gerekmez.
pause
exit /b 0

:error
cd /d "%~dp0.."
echo.
echo [HATA] Build tamamlanamadi. Yukaridaki hatayi kontrol edin.
pause
exit /b 1
