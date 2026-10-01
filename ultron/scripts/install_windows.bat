@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "%~dp0..\..\INSTALL.bat" %*
exit /b %errorlevel%
