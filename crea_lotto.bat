@echo off
chcp 65001 > nul
title birdsongtech - nuovo lotto da verificare
cd /d "%~dp0"

:: Numero di canti nel lotto da spedire al revisore
set QUANTI=40

echo ============================================================
echo   BIRDSONGTECH - LOTTO DI CANTI DA FAR VERIFICARE
echo ============================================================
echo.
python pubblica.py --lotto %QUANTI%
if errorlevel 1 (
    echo [X] Errore: lotto non creato.
    pause
    exit /b 1
)
echo.
echo Allega il file .zip alla risposta. Il testo da incollare e' in docs\VERIFICHE.md
if exist lotti start "" lotti
pause
