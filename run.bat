@echo off
title DocsGuards - Medical Scheduling System
color 0B

echo.
echo  ============================================================
echo   ^|^|  DocsGuards - Medical On-Call Scheduling System  ^|^|
echo  ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please install Python 3.8+
    echo          from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo  [1/2] Installing dependencies...
pip install flask openpyxl -q --disable-pip-version-check
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo  [2/2] Starting DocsGuards server...
echo.
echo  ============================================================
echo   Open your browser at:   http://localhost:5000
echo   Press Ctrl + C to stop the server
echo  ============================================================
echo.

python app.py

pause
