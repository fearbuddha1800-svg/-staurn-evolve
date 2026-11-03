@echo off
REM =========================================================================
REM Quant HQ — Stop All Components
REM =========================================================================

setlocal enabledelayedexpansion

set BASE=%~dp0

echo ========================================================================
echo   Quant HQ — Stopping all components
echo ========================================================================
echo.

REM Stop cockpit (port 8490)
echo [INFO] Stopping cockpit server (port 8490)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8490') do (
    taskkill /PID %%a /F >nul 2>&1
    echo [OK] Killed PID %%a on port 8490
)

REM Stop trade-relay (port 8484)
echo [INFO] Stopping trade-relay (port 8484)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8484') do (
    taskkill /PID %%a /F >nul 2>&1
    echo [OK] Killed PID %%a on port 8484
)

REM Stop any other python components
echo [INFO] Stopping remaining Quant HQ processes...
taskkill /IM python.exe /F >nul 2>&1

echo.
echo ========================================================================
echo   All components stopped.
echo ========================================================================
pause
