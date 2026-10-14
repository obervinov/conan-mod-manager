@echo off
rem Builds dist\ConanModManager.exe from ConanModManager.spec (needs Python 3.10+ on Windows)
python -m pip install --upgrade "pyinstaller>=6,<7" -r requirements.txt || exit /b 1
python -m PyInstaller --noconfirm ConanModManager.spec
