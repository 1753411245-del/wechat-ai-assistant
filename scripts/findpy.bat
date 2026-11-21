@echo off
rem Locate a 64-bit Python and put the command into PY.
set "PY="
where py.exe >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto :done
for %%v in (313 312 311 310 39) do call :try "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
if defined PY goto :done
for %%v in (313 312 311 310 39) do call :try "C:\Python%%v\python.exe"
if defined PY goto :done
for %%v in (313 312 311 310 39) do call :try "%ProgramFiles%\Python%%v\python.exe"
if defined PY goto :done
where python.exe >nul 2>nul
if not errorlevel 1 set "PY=python"
:done
exit /b 0

:try
if defined PY exit /b 0
if not exist %1 exit /b 0
%1 -c "import sys;sys.exit(0 if sys.maxsize>2**32 else 1)" >nul 2>nul
if errorlevel 1 exit /b 0
set "PY=%~1"
exit /b 0
