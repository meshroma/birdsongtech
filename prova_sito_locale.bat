@echo off
chcp 65001 > nul
title birdsongtech - prova del sito sul PC
cd /d "%~dp0"
echo Prepara i dati usando gli audio della cartella audio\ (nessun caricamento online)...
python pubblica.py --locale
if errorlevel 1 ( pause & exit /b 1 )
echo.
echo Il sito e' aperto su http://localhost:8000  -  chiudi questa finestra per fermarlo.
echo IMPORTANTE: prima di pubblicare usa aggiorna_birdsong.bat, che rigenera i dati per il sito online.
start "" http://localhost:8000/index.html
python -m http.server 8000
