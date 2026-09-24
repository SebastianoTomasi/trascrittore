@echo off
rem Drag a meeting recording onto this file to get "<name> - trascrizione.txt" next to it.
rem Lives in the shared folder, next to the "voci" voice library and meeting.ini.
setlocal EnableExtensions
rem chcp reads the stdin it inherits: give it nul so typed or piped answers stay for set /p and docker.
chcp 65001 >nul <nul
title Trascrizione riunione

set "IMAGE=meeting-transcriber:pilot"
set "VOICES=%~dp0voci"
set "CONFIG=%~dp0meeting.ini"
set "CACHE=%LOCALAPPDATA%\MeetingTranscriber\cache"
set "RC=1"

if "%~1"=="" goto :no_file
if not exist "%~1" goto :missing_file
if not "%~2"=="" echo Trascrivo un file alla volta: ora "%~nx1", gli altri trascinali dopo.

docker info >nul 2>&1
if errorlevel 1 goto :no_docker
docker image inspect %IMAGE% >nul 2>&1
if errorlevel 1 goto :no_image

if not exist "%VOICES%" mkdir "%VOICES%"
if not exist "%CACHE%" mkdir "%CACHE%"

set "CONFIG_ARGS="
if exist "%CONFIG%" set CONFIG_ARGS=-v "%CONFIG%:/config/meeting.ini:ro" -e MEETING_CONFIG=/config/meeting.ini

:ask_speakers
set "SPEAKERS="
set "SPEAKERS_ARG="
set /p "SPEAKERS=Quante persone parlano nella riunione? (Invio = non lo so) "
if not defined SPEAKERS goto :run_gpu
echo(%SPEAKERS%| findstr /r /x "[1-9][0-9]*" >nul
if errorlevel 1 goto :bad_speakers
set "SPEAKERS_ARG=--speakers %SPEAKERS%"

:run_gpu
echo.
docker run --rm -i -e TZ=Europe/Rome --gpus all -v "%~dp1.:/audio" -v "%VOICES%:/voci:ro" -v "%CACHE%:/cache" %CONFIG_ARGS% %IMAGE% "/audio/%~nx1" %SPEAKERS_ARG% --ask-names
set "RC=%ERRORLEVEL%"
rem 125 means Docker itself could not start the container, typically because it has no GPU access.
if not "%RC%"=="125" goto :done

echo.
echo Docker non riesce a usare la GPU: riprovo sulla CPU, sara' molto piu' lento.
docker run --rm -i -e TZ=Europe/Rome -e MEETING_GPU_FALLBACK=docker -v "%~dp1.:/audio" -v "%VOICES%:/voci:ro" -v "%CACHE%:/cache" %CONFIG_ARGS% %IMAGE% "/audio/%~nx1" %SPEAKERS_ARG% --ask-names
set "RC=%ERRORLEVEL%"
goto :done

:bad_speakers
echo Scrivi un numero (per esempio 4), oppure premi solo Invio.
goto :ask_speakers

:no_file
echo Trascina il file audio della riunione sopra Trascrivi.bat.
goto :done

:missing_file
echo File non trovato: %~1
goto :done

:no_docker
echo Docker Desktop non e' avviato. Aprilo, aspetta che sia pronto e riprova.
goto :done

:no_image
echo Il trascrittore non e' installato: esegui prima Installa.bat.
goto :done

:done
echo.
if not "%RC%"=="0" echo Qualcosa e' andato storto: leggi i messaggi qui sopra.
pause
endlocal
