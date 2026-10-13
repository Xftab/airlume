@echo off
rem Run the test suite.
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m pytest -q
endlocal
