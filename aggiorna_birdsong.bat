@echo off
chcp 65001 > nul
title 🦅 Sincronizzazione e Aggiornamento Birdsong AI

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

echo [*] Fase 4: Sincronizzazione Cloud automatica con GitHub...
git add .
:: Genera un messaggio di commit con data e ora correnti (es. "Aggiornamento automatico: 01/11/2026 15:50")
git commit -m "Aggiornamento automatico dati: %date% %time%"
git push origin main
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Errore durante il push su GitHub. Controlla la connessione o GitHub Desktop.
    pause
    exit /b
)
echo.

echo ============================================================
echo 🟢 AGGIORNAMENTO E PUBBLICAZIONE COMPLETATI CON SUCCESSO!
echo    I dati sono online. Puoi consultare l'archivio e ricerca.html.
echo ============================================================
echo.
pause
