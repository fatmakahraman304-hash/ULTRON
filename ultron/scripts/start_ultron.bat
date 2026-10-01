@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0..\..\START.bat" %*
exit /b %errorlevel%
