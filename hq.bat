@echo off
rem Quant HQ control CLI wrapper - runs hq.py with the miniconda interpreter and
rem without the inherited PYTHONPATH (which would shadow the venv packages).
setlocal
set "PYTHONPATH="
set "PY=C:\Users\voidk\miniconda3\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0hq.py" %*
exit /b %ERRORLEVEL%
