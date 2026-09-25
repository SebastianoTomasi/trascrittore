@echo off
rem Load the transcriber image from trascrittore.tar next to this file.
setlocal EnableExtensions
chcp 65001 >nul <nul
title Installazione trascrittore

set "IMAGE=trascrittore:latest"
set "IMAGE_TAR=%~dp0trascrittore.tar"

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
rem Versions installed before the rename used other names: free their disk space and the voiceprints in their cache.
docker image inspect meeting-transcriber:pilot >nul 2>&1
if not errorlevel 1 docker rmi meeting-transcriber:pilot >nul 2>&1
if exist "%LOCALAPPDATA%\MeetingTranscriber" rmdir /s /q "%LOCALAPPDATA%\MeetingTranscriber"
if exist "%~dp0meeting.ini" echo Il file meeting.ini non serve piu': se avevi cambiato qualcosa, scrivi solo quelle righe in trascrittore.ini, poi cancellalo.
if not exist "%LOCALAPPDATA%\Trascrittore\cache" mkdir "%LOCALAPPDATA%\Trascrittore\cache"
echo.
echo Controllo la GPU...
docker run --rm --gpus all --entrypoint python %IMAGE% -c "import torch; print('GPU pronta: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'ATTENZIONE: Docker non vede la GPU')"
if errorlevel 1 echo ATTENZIONE: Docker non riesce a usare la GPU. Il trascrittore funzionera' sulla CPU, molto piu' lento.

rem The launcher creates trascrittore.ini the first time, and installs the agent skill of this version every time.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0trascrittore.ps1" install

echo.
echo Installazione completata. Per trascrivere, trascina una registrazione su Trascrivi.bat.
goto :end

:no_docker
echo Docker Desktop non e' avviato. Aprilo, aspetta che sia pronto e riprova.
goto :end

:missing_tar
echo Non trovo trascrittore.tar accanto a Installa.bat.
goto :end

:failed
echo Il caricamento non e' riuscito: leggi i messaggi qui sopra.

:end
echo.
pause
endlocal
