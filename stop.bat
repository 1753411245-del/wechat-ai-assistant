@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*wxa.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Output ('killed ' + $_.ProcessId) }"
echo stopped
timeout /t 3 >nul
