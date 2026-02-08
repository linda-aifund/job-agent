@echo off
REM Job Agent - Windows Task Scheduler Setup
REM Creates a weekly scheduled task to run the job agent every Monday at 11:00 AM
REM Uses PowerShell cmdlets for Microsoft account compatibility (S4U logon)
REM Run as Administrator

cd /d "%~dp0"

set TASK_NAME=DailyJobAgent
set RUN_SCRIPT=%~dp0run.bat

echo Creating scheduled task: %TASK_NAME%
echo Script: %RUN_SCRIPT%
echo Schedule: Weekly on Mondays at 11:00 AM
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Unregister-ScheduledTask -TaskName '%TASK_NAME%' -Confirm:$false -ErrorAction SilentlyContinue;" ^
    "$action = New-ScheduledTaskAction -Execute '%RUN_SCRIPT%' -WorkingDirectory '%~dp0';" ^
    "$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 11:00AM;" ^
    "$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest;" ^
    "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries;" ^
    "Register-ScheduledTask -TaskName '%TASK_NAME%' -Action $action -Trigger $trigger -Principal $principal -Settings $settings;" ^
    "if ($?) { Write-Host 'Task configured successfully!'; Write-Host '  - Runs every Monday at 11:00 AM'; Write-Host '  - Runs whether or not user is logged in (S4U)'; Write-Host '  - StartWhenAvailable: ON'; Write-Host '  - WakeToRun: ON' } else { Write-Host 'Failed to create task. Try running as Administrator.'; exit 1 }"

echo.
echo To verify: schtasks /Query /TN %TASK_NAME% /V /FO LIST
echo To delete:  schtasks /Delete /TN %TASK_NAME% /F
echo To run now: schtasks /Run /TN %TASK_NAME%

pause
