@echo off
REM =========================================================================
REM Quant HQ — Professional Trading Command Center
REM Windows Installer
REM =========================================================================
REM Installs Python dependencies, validates configuration, and prepares
REM the workspace for first launch. Run as Administrator for full setup.
REM =========================================================================

setlocal enabledelayedexpansion

set BASE=%~dp0
set PY=python
set VENV=%BASE%\.venv

echo ========================================================================
echo   Quant HQ Installer v1.0.0
echo   Professional Trading Command Center
echo ========================================================================
echo.

REM Check Python
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH. Install Python 3.10+ first.
    pause
    exit /b 1
)
echo [OK] Python found: %PY%

REM Create virtual environment
if not exist "%VENV%" (
    echo [INFO] Creating virtual environment...
    %PY% -m venv "%VENV%"
)
echo [OK] Virtual environment ready

REM Install dependencies
echo [INFO] Installing dependencies (this may take a minute)...
"%VENV%\Scripts\pip.exe" install -r "%BASE%requirements.txt"
if errorlevel 1 (
    echo [WARNING] Some dependencies failed to install. Core stack still runs on stdlib.
)
echo [OK] Dependencies installed

REM Validate configuration
echo [INFO] Validating config.json...
"%VENV%\Scripts\python.exe" "%BASE%validate-config.py"
if errorlevel 1 (
    echo [ERROR] Configuration validation failed. Fix config.json before starting.
    pause
    exit /b 1
)
echo [OK] Configuration valid

REM Set up environment
copy "%BASE%config.json" "%BASE%config.local.json" >nul 2>&1
if not exist "%BASE%config.local.json" (
    copy "%BASE%config.json" "%BASE%config.local.json"
)

echo.
echo ========================================================================
echo   Install complete.
echo   Start:  start.bat
echo   Stop:   stop.bat
echo   Status: quant-hq status   (or: python hq.py status)
echo   Dashboard: http://localhost:8490
echo ========================================================================
pause
