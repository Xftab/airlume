@echo off
rem Register an hourly Windows scheduled task that runs collect.bat while you are logged in.
rem Run once:  K:\airlume\schedule     Remove with:  schtasks /Delete /TN "Airlume hourly collect" /F
schtasks /Create /SC HOURLY /MO 1 /TN "Airlume hourly collect" /TR "\"%~dp0collect.bat\"" /F
if errorlevel 1 (echo Could not create the task. & exit /b 1)
echo Hourly collection scheduled. Check with:  schtasks /Query /TN "Airlume hourly collect"
