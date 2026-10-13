@echo off
rem Collect one round of readings by hand (EPA Lahore + districts, Open-Meteo).
rem Usage:  collect          writes to data\archive and the local database
rem         collect --dry-run  fetches and prints only
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python scripts\collect_hourly.py %*
endlocal
