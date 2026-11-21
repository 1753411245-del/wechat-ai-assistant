@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
  echo [X] .venv not found. Run quickstart.bat first.
  pause & exit /b 1
)
if not exist "config.env" (
  echo [X] config.env not found. Run quickstart.bat first.
  pause & exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File src\check_running.ps1 >nul 2>&1
if not errorlevel 1 goto :loop
echo [service] already running, exit
timeout /t 5 >nul
exit /b 0

:loop
echo [%date% %time%] === service start === >> logs\run.log
.venv\Scripts\python.exe -u src\wxa.py >> logs\run.log 2>&1
echo [%date% %time%] === service exit code %errorlevel% === >> logs\run.log
timeout /t 15 >nul
goto :loop
