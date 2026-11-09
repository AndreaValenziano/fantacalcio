@echo off
rem Doppio clic per avviare il Consigliere di formazione su Windows.
chcp 65001 >nul
cd /d "%~dp0"
set PY=
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Non trovo Python 3.11 o successivo. Installalo seguendo GUIDA.md, poi riprova.
  pause
  exit /b 1
)
%PY% -m consigliere
if errorlevel 1 pause
