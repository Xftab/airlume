@echo off
rem Start the Airlume app in the browser.  Press Ctrl+C in this window to stop it.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run  K:\airlume\setup  first. & exit /b 1)
call .venv\Scripts\activate.bat
python scripts\check_secrets.py || exit /b 1
streamlit run airlume\app\streamlit_app.py --server.headless true --browser.gatherUsageStats false
endlocal
