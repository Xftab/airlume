@echo off
rem Save Airlume: commit every change and push it to GitHub.
rem Usage:  save "what changed"
setlocal
cd /d "%~dp0"
if "%~1"=="" (set "MSG=Update project files") else (set "MSG=%~1")
git add -A
git diff --cached --quiet
if errorlevel 1 git commit -m "%MSG%"
rem Pull first: GitHub may have committed rebuilt PDFs since the last save.
git pull --rebase --autostash
git push
echo.
echo Saved and pushed: %MSG%
endlocal
