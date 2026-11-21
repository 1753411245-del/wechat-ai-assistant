@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" ( echo Run quickstart.bat first & pause & exit /b 1 )
.venv\Scripts\python.exe src\report.py --days 1 > logs\report.txt 2>&1
type logs\report.txt
.venv\Scripts\python.exe src\report.py --html logs\report.html >nul 2>&1
start "" "logs\report.html"
timeout /t 5 >nul
