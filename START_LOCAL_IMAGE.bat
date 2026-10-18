@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo GOLGE: Once mevcut Python kurulumu gerekli.
  exit /b 2
)
".venv\Scripts\python.exe" scripts\golge_comfyui_start.py
exit /b %errorlevel%
