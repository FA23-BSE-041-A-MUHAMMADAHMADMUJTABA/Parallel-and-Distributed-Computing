@echo off
title CSC-334: Remote Worker Server Node (Computer B)
cd /d "%~dp0"
echo ======================================================================
echo   CSC-334: REMOTE WORKER SERVER NODE (COMPUTER B)
echo ======================================================================
echo.

echo   Your LAN IP Addresses (Enter one of these on Computer A):
echo   ----------------------------------------------------------
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    echo     IP:%%a
)
echo   ----------------------------------------------------------
echo.

netsh advfirewall firewall show rule name="CSC334-Lab4-TCP5000" >nul 2>&1
if errorlevel 1 (
    netsh advfirewall firewall add rule name="CSC334-Lab4-TCP5000" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
)
netsh advfirewall firewall show rule name="CSC334-Lab4-UDP5005" >nul 2>&1
if errorlevel 1 (
    netsh advfirewall firewall add rule name="CSC334-Lab4-UDP5005" dir=in action=allow protocol=UDP localport=5005 >nul 2>&1
)

ipconfig | findstr /c:"169.254." >nul 2>&1
if not errorlevel 1 (
    echo   ----------------------------------------------------------
    echo   [!] NOTICE: APIPA (169.254.x.x) detected on Ethernet.
    echo       Direct LAN wire k liye Static IP set karna zaroori hai.
    echo       Quick Fix: Double-click 'setup_lan_ip_server.bat'
    echo   ----------------------------------------------------------
    echo.
)

echo ======================================================================
echo   [1] Launch Modern Server GUI Dashboard (Recommended)
echo   [2] Launch Command-Line Console Daemon (0.0.0.0:5000)
echo ======================================================================
set /p choice="Select Option [1 or 2] (Default 1): "
if "%choice%"=="2" (
    echo Starting Server CLI Daemon on 0.0.0.0:5000...
    python -u server_daemon.py --host 0.0.0.0 --port 5000
) else (
    echo Starting Modern Server GUI Dashboard...
    python server_gui.py
)
pause
