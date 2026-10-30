@echo off
rem Register an hourly Windows scheduled task that runs collect_push.bat while you
rem are logged in. collect_push fetches, writes the archive, commits and pushes.
rem Run once:  K:\airlume\schedule
rem Remove:    schtasks /Delete /TN "Airlume hourly collect" /F
rem Check:     schtasks /Query /TN "Airlume hourly collect" /V /FO LIST
rem
rem Since 28 Oct 2026 this is the primary collector for Punjab EPA data (stations,
rem districts, trend and forecast). Open-Meteo CAMS still runs in the cloud via
rem GitHub Actions (.github/workflows/collect.yml), unchanged.
rem
rem 30 Oct 2026. schtasks sets two power conditions by default: do not start on
rem battery, and stop if the machine switches to battery. On a laptop that is
rem almost always true, so the task was refused nearly every hour and only 3 of
rem the first 44 rounds ran. The symptom is Last Result -2147020576 (0x800710E0,
rem "the operator or administrator has refused the request") against a task whose
rem State is Enabled and whose Next Run Time looks healthy. Step 2 clears both
rem conditions and adds StartWhenAvailable, so a round missed while the laptop
rem slept runs on wake instead of being skipped. Every missed hour is lost for
rem good: the portal only serves the current reading, never history.

rem 1. Create (or replace) the hourly task.
schtasks /Create /SC HOURLY /MO 1 /TN "Airlume hourly collect" /TR "\"%~dp0collect_push.bat\"" /F
if errorlevel 1 (echo Could not create the task. & exit /b 1)

rem 2. Clear the power conditions schtasks just set. Without this the task is
rem    registered and enabled but refuses to start whenever you are unplugged.
powershell -NoProfile -Command "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew; Set-ScheduledTask -TaskName 'Airlume hourly collect' -Settings $s"
if errorlevel 1 (
  echo.
  echo Task created, but the power conditions could not be cleared.
  echo Open Task Scheduler, find "Airlume hourly collect", then Properties,
  echo Conditions, and untick both Power options by hand. Otherwise the
  echo collector will not run on battery.
  exit /b 1
)

echo.
echo Hourly collection scheduled and power conditions cleared.
echo Verify with:  schtasks /Query /TN "Airlume hourly collect" /V /FO LIST
echo Power Management should read "Battery Mode, Start On Batteries" and
echo Last Result should be 0 after the next round.
