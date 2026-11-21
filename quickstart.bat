@echo off
setlocal
cd /d "%~dp0"
call scripts\findpy.bat
if not defined PY goto :nopython

echo ==============================================
echo   WeChat AI Assistant - first run setup
echo ==============================================
echo [*] Python: %PY%

if not exist ".venv\Scripts\python.exe" (
  echo [*] Creating .venv ...
  %PY% -m venv .venv
  if errorlevel 1 goto :venvfail
)
call ".venv\Scripts\activate.bat"

echo [*] Installing wechatauto-replica (skip winsdk) ...
python -m pip install -q --upgrade pip
python -m pip install wechatauto-replica --no-deps --timeout 60
if errorlevel 1 (
  python -m pip install wechatauto-replica --no-deps -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
  if errorlevel 1 goto :fail
)

echo [*] Installing dependencies ...
python -m pip install -r requirements.txt --timeout 60
if errorlevel 1 (
  python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
  if errorlevel 1 goto :fail
)

python -c "import wechatauto;print('[OK] wechatauto', getattr(wechatauto,'__version__','?'))"
if errorlevel 1 goto :fail

if not exist "config.env" (
  echo.
  echo [*] No config.env yet, starting the setup wizard ...
  python src\setup.py
  if not exist "config.env" goto :nocfg
)

echo.
echo [*] Starting the bot (Ctrl+C or stop.bat to stop)
echo.
python -u src\wxa.py
echo.
echo [*] stopped
pause
exit /b 0

:nopython
echo [X] Python not found. Install 64-bit Python 3.10+ and tick "Add python.exe to PATH".
pause
exit /b 1
:venvfail
echo [X] venv creation failed.
pause
exit /b 1
:fail
echo [X] dependency install failed, see the error above.
pause
exit /b 1
:nocfg
echo [X] config.env was not created.
pause
exit /b 1
