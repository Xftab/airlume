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
rem Pull first. If the same file changed on both sides, keep the laptop version.
git pull -q --rebase -X theirs --autostash
if errorlevel 1 (
  git rebase --abort 2>nul
  echo.
  echo PULL FAILED. Nothing was lost. Send Claude a screenshot of this window.
  exit /b 1
)
git push -q
if errorlevel 1 (
  echo.
  echo PUSH FAILED. Your work is saved on this laptop. Check the internet, then run save again.
  exit /b 1
)
echo.
if defined DID (echo Saved and pushed: %MSG%) else (echo Nothing new to save. Synced with GitHub.)
endlocal
