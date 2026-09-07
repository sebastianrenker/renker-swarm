@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   Renker Swarm - local run
echo   (Reads your key from the .env file.)
echo ============================================
echo Installing dependencies (first run only)...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo pip install failed - is Python installed and on PATH?
  pause
  exit /b 1
)
echo.
echo Starting the swarm. Leave this window open. Press Ctrl+C to stop.
echo.
python daemon.py
pause
