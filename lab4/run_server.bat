@echo off
title Remote Worker Node Daemon (Port 5000)
cd /d "%~dp0.."
echo ======================================================================
echo   CSC-334: REMOTE GPU TASK EXECUTION ENGINE DAEMON
echo ======================================================================
python -u lab4/server/server_daemon.py --host 127.0.0.1 --port 5000
pause
