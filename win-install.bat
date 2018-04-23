@echo off
python --version 2>NUL
if errorlevel 1 goto errorNoPython
cd /d %~dp0
virtualenv venv
CALL venv/Scripts/activate.bat
pip install -r requirements-win.txt
echo Environment setup complete.
pause
deactivate

:errorNoPython
echo Error^: Python not installed
