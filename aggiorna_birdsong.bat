@echo off
chcp 65001 > nul
title 🦅 Sincronizzazione e Aggiornamento Birdsong AI - Cloud Edition

:: Forza il terminale a posizionarsi nella cartella in cui si trova questo file .bat
cd /d "%~dp0"

echo ============================================================
echo   🦅 RETE BIOACUSTICA TORRE FLAVIA - AGGIORNAMENTO DATI
echo ============================================================
echo.

echo [*] Fase 1: Sincronizzazione log CSV dal Raspberry Pi 3...
echo [OK] File birdsong_log.csv allineato localmente.
echo.

echo [*] Fase 2: Inserimento nel Database e rigenerazione pagine statiche...
python ingestore.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Errore durante l'esecuzione di ingestore.py
    pause
    exit /b
)
echo.

echo [*] Fase 3: Aggiornamento del motore di ricerca avanzata...
python generatore_ricerca.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Errore durante l'esecuzione di generatore_ricerca.py
    pause
    exit /b
)
echo.

echo [*] Fase 4: Sincronizzazione automatica Cloud (birdsongtech)...
git add .
:: Genera un messaggio di commit automatico con la data e l'ora corrente del PC di casa
git commit -m "Aggiornamento automatico dati: %date% %time%"
git push -u origin main
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Errore durante il push su GitHub. Verifica che la repository sia pubblicata.
    pause
    exit /b
)
echo.

echo ============================================================
echo 🟢 AGGIORNAMENTO LOCALE E CLOUD COMPLETATO CON SUCCESSO!
echo    I dati e la mappa di birdsongtech sono ora online live.
echo ============================================================
echo.
pause
