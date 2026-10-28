@echo off
rem Register an hourly Windows scheduled task that runs collect_push.bat while you
rem are logged in. collect_push fetches, writes the archive, commits and pushes.
rem Run once:  K:\airlume\schedule
rem Remove:    schtasks /Delete /TN "Airlume hourly collect" /F
rem Check:     schtasks /Query /TN "Airlume hourly collect"
rem
rem Since 28 Oct 2026 this is the primary collector for Punjab EPA data (stations,
rem districts, trend and forecast). Open-Meteo CAMS still runs in the cloud via
rem GitHub Actions (.github/workflows/collect.yml), unchanged.
schtasks /Create /SC HOURLY /MO 1 /TN "Airlume hourly collect" /TR "\"%~dp0collect_push.bat\"" /F
if errorlevel 1 (echo Could not create the task. & exit /b 1)
echo Hourly collection scheduled. Check with:  schtasks /Query /TN "Airlume hourly collect"
