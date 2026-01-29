@echo off
REM JKU MTB Analyzer - Windows Launcher
REM Double-click this file to start the application!

echo.
echo ========================================================
echo   JKU Mitteilungsblatt Analyzer v1.15
echo   AI-powered relevance filtering for university bulletins
echo ========================================================
echo.

REM Get the directory where this batch file is located
set "BATCH_DIR=%~dp0"

REM Convert Windows path to WSL path
REM e.g., C:\Users\bob\JKU-MTB-Analyzer\ becomes /mnt/c/Users/bob/JKU-MTB-Analyzer/
set "WSL_PATH=%BATCH_DIR%"
set "WSL_PATH=%WSL_PATH:\=/%"
set "WSL_PATH=%WSL_PATH:C:=/mnt/c%"
set "WSL_PATH=%WSL_PATH:D:=/mnt/d%"
set "WSL_PATH=%WSL_PATH:E:=/mnt/e%"

echo Starting from: %BATCH_DIR%
echo.

REM Run the shell script via WSL
wsl.exe bash -c "cd '%WSL_PATH%' && chmod +x start-mtb-analyzer.sh && ./start-mtb-analyzer.sh"

pause
