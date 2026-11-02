@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
title Build Computer A and Computer B EXE files

echo ================================================================
echo CSC-334 - Build Windows Client and Server EXE files
echo ================================================================
echo.

where.exe py >nul 2>&1
if errorlevel 1 goto :no_python_launcher

rem Prefer a supported Python already installed on this PC.
set "PYTHON_VERSION="
py -3.13 --version >nul 2>&1
if not errorlevel 1 set "PYTHON_VERSION=3.13"
if defined PYTHON_VERSION goto :python_found

py -3.12 --version >nul 2>&1
if not errorlevel 1 set "PYTHON_VERSION=3.12"
if defined PYTHON_VERSION goto :python_found

py -3.11 --version >nul 2>&1
if not errorlevel 1 set "PYTHON_VERSION=3.11"
if defined PYTHON_VERSION goto :python_found

goto :no_compatible_python

:python_found
echo Using installed Python %PYTHON_VERSION% (64-bit is recommended).
echo.

if exist ".build_venv\Scripts\python.exe" goto :venv_ready

echo Creating isolated build environment...
py -%PYTHON_VERSION% -m venv ".build_venv"
if errorlevel 1 goto :failed

:venv_ready
echo Installing build dependencies...
".build_venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed

".build_venv\Scripts\python.exe" -m pip install -r "requirements-build.txt"
if errorlevel 1 goto :failed

echo Building the two one-file Windows applications...
".build_venv\Scripts\python.exe" "scripts\build_windows.py"
if errorlevel 1 goto :failed

echo.
echo BUILD COMPLETE.
echo EXE files are inside the release folder.
echo Copy ComputerA_Client.exe to Computer A.
echo Copy ComputerB_Server.exe to Computer B.
echo.
pause
exit /b 0

:no_python_launcher
echo ERROR: Python Launcher py.exe was not found.
echo Install Python 3.11, 3.12, or 3.13 x64 from python.org.
echo During installation, enable the Python Launcher and Add Python to PATH.
echo.
pause
exit /b 1

:no_compatible_python
echo ERROR: No supported Python 3.11, 3.12, or 3.13 installation was found.
echo Installed Python versions reported by the launcher:
py --list
echo.
echo Install Python 3.11, 3.12, or 3.13 x64 from python.org, then run this file again.
echo.
pause
exit /b 1

:failed
echo.
echo BUILD FAILED. Read the error above and check the build prerequisites.
echo.
pause
exit /b 1
