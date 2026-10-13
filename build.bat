@echo off
rem Builds dist\ConanModManager.exe (needs Python 3.10+ on Windows)
python -m pip install --upgrade pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --onefile --windowed --name ConanModManager main.py
