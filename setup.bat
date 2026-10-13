@echo off
rem One-time setup on the laptop: create the virtual environment on K: and install packages.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment in %CD%\.venv ...
  "C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" -m venv .venv
  if errorlevel 1 (echo Could not create the venv. Check the Python path in setup.bat. & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (echo Package install failed. Check the internet, then run setup again. & exit /b 1)
if not exist ".env" copy .env.example .env >nul
python scripts\check_secrets.py
echo.
echo Setup done. Next: run   K:\airlume\run
endlocal
