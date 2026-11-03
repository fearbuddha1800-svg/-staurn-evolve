@echo off
REM =========================================================================
REM Quant HQ — Unified Startup Script
REM Starts all components of the trading command center:
REM   1. Cockpit server (UI + API) on http://localhost:8490
REM   2. Trade-relay (MT5 execution proxy) on http://localhost:8484
REM =========================================================================

setlocal enabledelayedexpansion

set BASE=%~dp0
set PY=%BASE%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

echo ========================================================================
echo   Quant HQ v1.0.0 — Starting all components
echo ========================================================================
echo.

REM Validate config first
echo [INFO] Validating configuration...
"%PY%" "%BASE%validate-config.py" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Config validation warnings — proceeding anyway.
)

REM Start cockpit server (port 8490)
echo [INFO] Starting cockpit server on http://localhost:8490 ...
start "QuantHQ-Cockpit" /b /d "%BASE%" "%PY%" -m cockpit --log cockpit.log 2>&1 | findstr /v "^$" > cockpit.log &
timeout /t 3 >nul
echo [OK] Cockpit server starting (PID in cockpit.log)

REM Start trade-relay (port 8484)
echo [INFO] Starting trade-relay on http://localhost:8484 ...
if exist "%BASE%trade-relay\package.json" (
    start "QuantHQ-TradeRelay" /b /d "%BASE%trade-relay" node trade-relay.js --port 8484 --log trade-relay.log 2>&1 | findstr /v "^$" > trade-relay.log &
) else (
    echo [WARNING] trade-relay not found at trade-relay/ — skipping.
)
timeout /t 3 >nul
echo [OK] Trade-relay starting (PID in trade-relay.log)

REM Wait briefly for services to come up
echo [INFO] Waiting for services to be ready...
timeout /t 5 >nul

REM Health check
echo [INFO] Running health check...
"%PY%" -c "
import urllib.request, json, sys
ok = True
for name, port, path in [
    ('Cockpit', 8490, '/api/state'),
    ('Trade-relay', 8484, '/'),
]:
    try:
        req = urllib.request.urlopen('http://localhost:%d%s' % (port, path), timeout=5)
        print('  [OK] %s on port %d — HTTP %d' % (name, port, req.status))
    except Exception as e:
        print('  [FAIL] %s on port %d — %s' % (name, port, e))
        ok = False
if not ok:
    sys.exit(1)
print()
print('All services running. Dashboard: http://localhost:8490')
" 2>&1

echo.
echo ========================================================================
echo   Quant HQ is running.
echo   Dashboard: http://localhost:8490
echo   Logs: cockpit.log, trade-relay.log
echo   Stop:   stop.bat
echo ========================================================================
