@echo off
python -c "import sys; sys.exit(sys.version_info[0] < 3 or sys.version_info[1] < 3 )" 2>NUL
if errorlevel 1 goto errorNoPython
cd /d %~dp0
python -m venv venv-win
CALL venv-win/Scripts/activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Environment setup complete.

pyinstaller --noconfirm --add-data "Plugins;Plugins" --additional-hooks-dir "hooks" %* smarthash.py
move dist\smarthash\magic\libmagic\* .\dist\smarthash
echo Build complete.
deactivate

echo Environment break down complete.
:errorNoPython
    echo Error^: Python > 3.3 not installed
