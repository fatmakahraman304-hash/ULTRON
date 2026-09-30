@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\bootstrap.ps1" -Mode install %*
set "result=%errorlevel%"
if not "%result%"=="0" echo HATA: Islem tamamlanamadi. logs klasorunu kontrol edin.
exit /b %result%
