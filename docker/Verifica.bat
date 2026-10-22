@echo off
rem Double-click to check how well this PC's voice library recognizes voices.
rem Transcripts dropped on it are checked too.
rem Nothing is changed without asking: the suggested threshold is only shown.
setlocal EnableExtensions
chcp 65001 >nul <nul
title Verifica riconoscimento voci

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0trascrittore.ps1" verify %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" echo Qualcosa e' andato storto: leggi i messaggi qui sopra.
pause
endlocal
