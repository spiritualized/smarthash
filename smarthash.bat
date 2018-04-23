@echo off
python --version > NUL 2>&1
if errorlevel 1 goto errorNoPython

SET cwd=%cd%
cd /d %~dp0
CALL venv/Scripts/activate.bat
cd /d %cwd%
smarthash.py %*
deactivate
@echo on

goto:eof

:errorNoPython
@echo on
echo Error^: Python not installed
