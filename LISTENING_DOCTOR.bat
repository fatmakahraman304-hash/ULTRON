@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_CMD=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
echo ULTRON: Gercek Qwen analiz ve bulut baglanti testi
echo Bu test kisisel konusma veya sifre gondermez.
"%PYTHON_CMD%" "scripts\ultron_listening_doctor.py"
set "RESULT=%errorlevel%"
echo.
if "%RESULT%"=="0" (
  echo TEST TAMAMLANDI: Tum yerel kontroller basarili.
) else (
  echo DIKKAT: Kontrollerden biri basarisiz. Ekrandaki sebebi inceleyin.
)
pause
exit /b %RESULT%
