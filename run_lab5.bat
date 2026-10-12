@echo off
title CSC-334 Bluetooth Offline Ludo Multiplayer Studio
cd /d "%~dp0Lab5(ludo with bluetooth)"
echo ======================================================================
echo   CSC-334: ALL-IN-ONE BLUETOOTH & OFFLINE LUDO MULTIPLAYER STUDIO
echo ======================================================================
echo   Launching Ludo Studio on Computer / Mobile...
echo ======================================================================
python -c "import qrcode" 2>nul || python -m pip install qrcode pillow --quiet
python ludo.py
pause
