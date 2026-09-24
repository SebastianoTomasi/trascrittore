@echo off
rem Drag a recording onto this file to get "<name> - trascrizione.txt" next to it,
rem or drag a "<name> - trascrizione.json" to name its voices later.
rem The questions live in trascrittore.ps1, which asks them and then runs the same commands an agent runs.
setlocal EnableExtensions
rem chcp reads the stdin it inherits: give it nul so typed answers stay for the questions.
chcp 65001 >nul <nul
title Trascrittore
set "RC=1"

if "%~1"=="" goto :no_file
if not exist "%~1" goto :missing_file
if not "%~2"=="" echo Trascrivo un file alla volta: ora "%~nx1", gli altri trascinali dopo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0trascrittore.ps1" interactive "%~1"
set "RC=%ERRORLEVEL%"
goto :done

:no_file
echo Trascina sopra Trascrivi.bat una registrazione, oppure un file "- trascrizione.json" per dare i nomi alle voci.
goto :done

:missing_file
echo File non trovato: %~1
goto :done

:done
echo.
if not "%RC%"=="0" echo Qualcosa e' andato storto: leggi i messaggi qui sopra.
pause
endlocal
