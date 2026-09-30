@echo off
setlocal EnableExtensions
chcp 65001 >nul <nul
title Installazione trascrittore
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0trascrittore.ps1" setup
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%
