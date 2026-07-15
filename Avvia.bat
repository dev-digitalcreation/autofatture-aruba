@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Autofatture reverse charge - Aruba

REM --- 1) Cerca Python -------------------------------------------------------
set "PY="
where py  >nul 2>&1 && set "PY=py"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )

if not defined PY (
  echo.
  echo  Python non risulta installato.
  echo  Apro la pagina di download: installa Python 3 e, nella prima schermata,
  echo  spunta la casella "Add python.exe to PATH". Poi rilancia questo file.
  echo.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)

REM --- 2) Primo avvio: crea ambiente e installa le librerie -------------------
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo  Primo avvio: preparo l'ambiente. Puo' richiedere 1-2 minuti...
  echo.
  %PY% -m venv .venv
  if errorlevel 1 ( echo Errore nella creazione dell'ambiente. & pause & exit /b 1 )
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip >nul 2>&1
  python -m pip install -r requirements.txt
  if errorlevel 1 ( echo Errore nell'installazione delle librerie. & pause & exit /b 1 )
) else (
  call ".venv\Scripts\activate.bat"
)

REM --- 3) Avvia l'app --------------------------------------------------------
echo  Avvio in corso... (il primo avvio puo' richiedere piu' tempo)
python main.py
if errorlevel 1 pause
