@echo off
REM Job Agent - Windows Task Scheduler Setup
REM Creates a daily scheduled task to run the job agent at 8:00 AM

cd /d "%~dp0"

set TASK_NAME=DailyJobAgent
set RUN_SCRIPT=%~dp0run.bat

echo Creating scheduled task: %TASK_NAME%
echo Script: %RUN_SCRIPT%
echo Schedule: Daily at 08:00 AM
echo.

schtasks /Create /TN "%TASK_NAME%" /TR "\"%RUN_SCRIPT%\"" /SC DAILY /ST 08:00 /F /RL HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Task created successfully!
    echo.
    echo To verify: schtasks /Query /TN %TASK_NAME% /V
    echo To delete:  schtasks /Delete /TN %TASK_NAME% /F
    echo To run now: schtasks /Run /TN %TASK_NAME%
) else (
    echo.
    echo Failed to create task. Try running this script as Administrator.
)

pause
