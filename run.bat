@echo off
rem Start the Airlume app in the browser.  Press Ctrl+C in this window to stop it.
rem The app reads data\archive, which the hourly cloud collector keeps current on GitHub;
rem run  K:\airlume\save  first to pull the latest rows.  Add  --collect  to fetch locally as well.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run  K:\airlume\setup  first. & exit /b 1)
call .venv\Scripts\activate.bat
python scripts\check_secrets.py || exit /b 1
if /I "%~1"=="--collect" (echo Fetching the latest readings... & python scripts\collect_hourly.py)
streamlit run airlume\app\streamlit_app.py --server.headless true --browser.gatherUsageStats false
endlocal
