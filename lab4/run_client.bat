@echo off
title CSC-334: Video Offload Client Node (Computer A)
cd /d "%~dp0client"
echo ======================================================================
echo   CSC-334: VIDEO OFFLOAD CLIENT NODE (COMPUTER A)
echo ======================================================================
echo.
echo   This Computer's IP Addresses:
echo   ----------------------------------------------------------
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    echo     IP:%%a
)
echo   ----------------------------------------------------------
echo.

ipconfig | findstr /c:"169.254." >nul 2>&1
if not errorlevel 1 (
    echo   ----------------------------------------------------------
    echo   [!] NOTICE: APIPA 169.254.x.x detected on Ethernet.
    echo       Direct LAN wire k liye Static IP set karna zaroori hai.
    echo       Quick Fix: Double-click setup_lan_ip_client.bat
    echo   ----------------------------------------------------------
    echo.
)

echo   Starting Client GUI...
echo.
python client_gui.py
pause
