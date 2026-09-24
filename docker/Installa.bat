@echo off
rem Load the meeting transcriber image from meeting-transcriber.tar next to this file.
setlocal EnableExtensions
chcp 65001 >nul <nul
title Installazione trascrittore riunioni

set "IMAGE=meeting-transcriber:pilot"
set "IMAGE_TAR=%~dp0meeting-transcriber.tar"

docker info >nul 2>&1
if errorlevel 1 goto :no_docker
if not exist "%IMAGE_TAR%" goto :missing_tar

rem Remember the installed version: after an update the old copy would keep its disk space.
set "OLD_ID="
for /f "delims=" %%i in ('docker image inspect -f "{{.Id}}" %IMAGE% 2^>nul') do set "OLD_ID=%%i"

echo Carico il trascrittore in Docker: ci vuole qualche minuto.
docker load -i "%IMAGE_TAR%"
if errorlevel 1 goto :failed

set "NEW_ID="
for /f "delims=" %%i in ('docker image inspect -f "{{.Id}}" %IMAGE% 2^>nul') do set "NEW_ID=%%i"
if not defined OLD_ID goto :check_gpu
if "%OLD_ID%"=="%NEW_ID%" goto :check_gpu
echo Rimuovo la versione precedente...
docker rmi %OLD_ID% >nul 2>&1

:check_gpu
if not exist "%LOCALAPPDATA%\MeetingTranscriber\cache" mkdir "%LOCALAPPDATA%\MeetingTranscriber\cache"
echo.
echo Controllo la GPU...
docker run --rm --gpus all --entrypoint python %IMAGE% -c "import torch; print('GPU pronta: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'ATTENZIONE: Docker non vede la GPU')"
if errorlevel 1 echo ATTENZIONE: Docker non riesce a usare la GPU. Il trascrittore funzionera' sulla CPU, molto piu' lento.

rem The agent skill always comes with the image of the same version, so it is installed every time.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0trascrittore.ps1" install-skill

echo.
echo Installazione completata. Per trascrivere, trascina una registrazione su Trascrivi.bat.
goto :end

:no_docker
echo Docker Desktop non e' avviato. Aprilo, aspetta che sia pronto e riprova.
goto :end

:missing_tar
echo Non trovo meeting-transcriber.tar accanto a Installa.bat.
goto :end

:failed
echo Il caricamento non e' riuscito: leggi i messaggi qui sopra.

:end
echo.
pause
endlocal
