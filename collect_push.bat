@echo off
rem Airlume: hourly collect + commit + push, from the laptop.
rem
rem WHY THIS EXISTS. From 25 Oct 2026 the Punjab EPA portal stopped answering
rem GitHub Actions runners (likely an IP geo-block on datacenter addresses). The
rem portal is fine from a Pakistan residential IP, so the EPA fetch is done on
rem the laptop again and pushed to GitHub. Open-Meteo CAMS still runs in the
rem cloud. Both machines run every source, so both write the same month files;
rem see step 3 for how that conflict is now handled.
rem
rem Run by Windows Task Scheduler (registered by schedule.bat). Safe to run
rem while editing the project: it only commits data\archive, pulls with
rem --autostash, and only pushes if there is something new.
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat

rem 1. Fetch and write to the CSV archive.
python scripts\collect_hourly.py
if errorlevel 1 (
  echo [collect_push] every source failed; nothing to push
  exit /b 1
)

rem 2. Stage only data\archive. Any other working-tree changes stay untouched.
git add data\archive
git diff --cached --quiet
if errorlevel 1 (
  git commit -q -m "data hourly collection from laptop"
) else (
  echo [collect_push] nothing new to commit
  exit /b 0
)

rem 3. Pull with rebase. --autostash protects any work in progress from being clobbered.
rem    -X theirs keeps the laptop version of a conflicting hunk in any other file.
rem    6 Nov 2026: for the archive CSVs that was the cause of data loss. When the
rem    laptop woke after a night asleep, its CAMS rows and the cloud's CAMS rows were
rem    both appended at the same place, and -X theirs threw the cloud's away
rem    (7,215 rows lost between 24 Oct and 6 Nov, all restored from git history by
rem    scripts\recover_archive_rows.py). .gitattributes now gives data/archive/**/*.csv
rem    the built-in union merge, which keeps both sides' lines; -X theirs no longer
rem    applies to those files.
git pull -q --rebase -X theirs --autostash
if errorlevel 1 (
  git rebase --abort 2>nul
  echo [collect_push] pull failed; your work is safe locally. Run save by hand later.
  exit /b 1
)

rem 4. Push.
git push -q
if errorlevel 1 (
  echo [collect_push] push failed; your work is safe locally. Check the internet, then run save by hand.
  exit /b 1
)
echo [collect_push] pushed
endlocal
