@echo off
title T — AI Core
cd /d "%~dp0"

echo.
echo  ████████╗
echo     ██╔══╝
echo     ██║   
echo     ██║   
echo     ██║   — AI Core v1.0.0
echo     ╚═╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

:: Install brain deps if needed
if not exist "brain\.deps_installed" (
    echo  [SETUP] Installing brain dependencies...
    pip install -r brain\requirements.txt -q
    echo installed > brain\.deps_installed
    echo  [OK] Dependencies installed.
)

:: Start brain in background
echo  [START] Launching brain...
start /b /min cmd /c "cd brain && python main.py > ..\logs\brain.log 2>&1"

:: Wait for brain to be ready
echo  [WAIT] Waiting for brain to start...
timeout /t 3 /nobreak >nul

:: Check if brain started
powershell -Command "try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 7891); $c.Close(); Write-Host '[OK] Brain online' } catch { Write-Host '[WARN] Brain not responding yet — continuing' }"

:: Launch T UI
echo  [START] Launching T interface...
start "" "T.exe" 2>nul || (
    echo  [DEV] Built exe not found — launching dev mode...
    npm run tauri dev
)

echo.
echo  T is running. Close this window to keep T running in background.
echo  To stop T: close the T window or right-click tray icon.
echo.
pause
