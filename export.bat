@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" ( echo Run quickstart.bat first & pause & exit /b 1 )
.venv\Scripts\python.exe src\export_xlsx.py 30
start "" "data"
timeout /t 5 >nul
