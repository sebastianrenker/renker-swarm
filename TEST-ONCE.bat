@echo off
setlocal
cd /d "%~dp0"
echo Renker Swarm - single test cycle
python -m pip install -q -r requirements.txt
python run_once.py
echo.
echo (Check the outputs\ folder for results.)
pause
