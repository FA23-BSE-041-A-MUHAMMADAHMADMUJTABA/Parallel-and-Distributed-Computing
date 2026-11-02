@echo off
title Configure LAN Static IP for Computer A (Client)
echo ======================================================================
echo   CSC-334: AUTO-CONFIGURE STATIC IP (COMPUTER A - CLIENT)
echo ======================================================================
echo.

:: Check for Administrator privileges; if not elevated, request UAC
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Administrator privileges required to change IP settings.
    echo     Requesting elevation... Please click "Yes" on the UAC prompt.
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

echo [*] Setting Static IP on adapter 'Ethernet'...
echo     IPv4 Address : 192.168.1.10
echo     Subnet Mask  : 255.255.255.0
echo.
netsh interface ipv4 set address name="Ethernet" static 192.168.1.10 255.255.255.0

if %errorlevel% equ 0 (
    echo [OK] Static IP 192.168.1.10 assigned successfully to Ethernet!
) else (
    echo [!] Warning: Failed to set IP on 'Ethernet'. Check adapter name in ncpa.cpl.
)

echo [*] Opening Windows Firewall for Port 5000, Auto-Discovery UDP 5005 and Ping...
netsh advfirewall firewall add rule name="CSC334-Lab4-TCP5000" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
netsh advfirewall firewall add rule name="CSC334-Lab4-UDP5005" dir=in action=allow protocol=UDP localport=5005 >nul 2>&1
netsh advfirewall firewall add rule name="CSC334-Lab4-ICMP" dir=in action=allow protocol=ICMPv4 >nul 2>&1
echo [OK] Firewall rules configured!

echo.
echo ======================================================================
echo   SETUP COMPLETE!
echo   - Computer A (This PC) IP : 192.168.1.10
echo   - Computer B (Server) IP  : 192.168.1.20
echo.
echo   Ab Client GUI mai Computer B ka IP enter karein: 192.168.1.20
echo ======================================================================
pause

