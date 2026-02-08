@echo off
REM Job Agent - Run script
REM Activates the virtual environment and runs the job agent pipeline

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found. Run: python -m venv venv
    echo Then: venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

python -m job_agent.main %* >> "%~dp0logs\run.log" 2>&1
