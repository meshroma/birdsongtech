@echo off
chcp 65001 > nul
title birdsongtech - aggiornamento archivio e sito
cd /d "%~dp0"

:: ============================================================
::  CONFIGURAZIONE (facoltativa)
::  Per scaricare il log dal Raspberry Pi in automatico, compila
::  queste due righe (Windows 10/11 ha gia' il comando scp):
::    set PI_HOST=pi@192.168.1.50
::    set PI_LOG=/home/pi/birdsong/birdsong_log.csv
::  Se restano vuote, il log viene preso cosi' com'e' nella cartella.
::  Per non dover scrivere la password: vedi raspberry\LEGGIMI.md
:: ============================================================
set PI_HOST=pi@192.168.1.100
set PI_LOG=/home/pi/birdsong_log.csv
set PI_TELEMETRIA=/home/pi/telemetria.csv

echo ============================================================
echo   RETE BIOACUSTICA TORRE FLAVIA - AGGIORNAMENTO
echo ============================================================
echo.

echo [1/4] Log dal Raspberry Pi
if "%PI_HOST%"=="" (
    echo       Nessun Raspberry configurato: uso birdsong_log.csv presente nella cartella.
) else (
    scp "%PI_HOST%:%PI_LOG%" birdsong_log.csv
    if errorlevel 1 (
        echo [!] Download del log non riuscito: continuo con la copia gia' presente.
    ) else (
        echo       Log scaricato.
    )
    scp "%PI_HOST%:%PI_TELEMETRIA%" telemetria.csv
    if errorlevel 1 (
        echo [!] Telemetria non scaricata: le statistiche useranno i dati gia' presenti.
    ) else (
        echo       Telemetria scaricata.
    )
)
echo.

echo [2/4] Audio da importare
if exist "da_importare\*.wav" (
    echo       Trovati file .wav in da_importare\ : verranno associati ai rilevamenti.
) else (
    echo       Nessun .wav nuovo. Dopo lo scarico dalla XIAO copiali in da_importare\
)
echo.

echo [3/4] Database, Internet Archive e dati del sito
python pubblica.py
if errorlevel 1 (
    echo [X] Errore in pubblica.py: il sito NON e' stato aggiornato.
    pause
    exit /b 1
)
echo.

echo [4/4] Pubblicazione su GitHub
git add data birdsong_history.db birdsong_log.csv
if exist telemetria.csv git add telemetria.csv
git diff --cached --quiet
if errorlevel 1 (
    git commit -q -m "Dati: aggiornamento del %date% %time:~0,5%"
    echo       Dati salvati.
) else (
    echo       Nessun dato nuovo.
)
:: eventuali modifiche alle pagine o agli script finiscono in un commit separato
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -q -m "Sito: modifiche del %date% %time:~0,5%"
    echo       Modifiche al sito salvate.
)
git push -q origin main
if errorlevel 1 (
    echo [X] Push su GitHub non riuscito. Controlla la connessione o GitHub Desktop.
    pause
    exit /b 1
)
echo.
echo ============================================================
echo   FATTO. Il sito si aggiorna online entro un paio di minuti.
echo ============================================================
echo.
pause
