@echo off
rem Save Airlume: commit every change and push it to GitHub.
rem Usage:  save "what changed"
setlocal
cd /d "%~dp0"
if "%~1"=="" (set "MSG=Update project files") else (set "MSG=%~1")
set "DID="
git add -A
git diff --cached --quiet
if errorlevel 1 (git commit -q -m "%MSG%" & set "DID=1")
rem Pull first, in case anything was changed on GitHub directly.
git pull -q --rebase --autostash
git push -q
echo.
if defined DID (echo Saved and pushed: %MSG%) else (echo Nothing new to save. Synced with GitHub.)
endlocal
