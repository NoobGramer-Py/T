@echo off
title T — Shutdown
echo.
echo  [STOP] Shutting down T...

:: Stop brain process
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main.py*" >nul 2>&1
taskkill /F /IM python.exe /FI "COMMANDLINE eq *main.py*" >nul 2>&1

:: Stop T UI
taskkill /F /IM t-assistant.exe >nul 2>&1

:: Stop tray
taskkill /F /IM python.exe /FI "COMMANDLINE eq *tray.py*" >nul 2>&1

echo  [OK] T stopped.
timeout /t 2 /nobreak >nul
