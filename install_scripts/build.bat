@echo off
setlocal enabledelayedexpansion

REM === Configuration ===
set APP_NAME=ModbusSniffer
set MAIN_PY=..\src\modbus_sniffer_GUI.py
set ICON=..\images\icon.ico
set DIST_DIR=dist
set VENV_DIR=..\.venv

REM Shortcut paths
set DESKTOP_LINK=%USERPROFILE%\Desktop\%APP_NAME%.lnk
set STARTMENU_LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%APP_NAME%.lnk

echo.
echo ==== [1/6] Cleaning previous build ====
if exist %DIST_DIR% rmdir /s /q %DIST_DIR%
if exist %APP_NAME%.spec del /q %APP_NAME%.spec
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo ==== [2/6] Creating/activating virtual environment ====
if not exist %VENV_DIR% (
    python -m venv %VENV_DIR%
)
call %VENV_DIR%\Scripts\activate.bat

echo.
echo ==== [3/6] Installing dependencies ====
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo ==== [4/6] Building EXE with icon ====
pyinstaller --onefile --noconsole --icon=%ICON% --name %APP_NAME% %MAIN_PY%

echo.
echo ==== [5/6] Creating shortcuts ====
REM Desktop shortcut
powershell -Command "$desktop = [Environment]::GetFolderPath('Desktop'); $s = (New-Object -COM WScript.Shell).CreateShortcut(\"$desktop\ModbusSniffer.lnk\"); $s.TargetPath = \"$(Resolve-Path dist\ModbusSniffer.exe)\"; $s.IconLocation = \"$(Resolve-Path images\icon.ico)\"; $s.Save()"

REM Start Menu shortcut
powershell -Command "$startmenu = [Environment]::GetFolderPath('StartMenu'); $s = (New-Object -COM WScript.Shell).CreateShortcut(\"$startmenu\Programs\ModbusSniffer.lnk\"); $s.TargetPath = \"$(Resolve-Path dist\ModbusSniffer.exe)\"; $s.IconLocation = \"$(Resolve-Path images\icon.ico)\"; $s.Save()"

echo.
echo ==== [6/6] Done ====
echo EXE path: %DIST_DIR%\%APP_NAME%.exe
echo Desktop shortcut: %DESKTOP_LINK%
echo Start Menu shortcut: %STARTMENU_LINK%

call deactivate
pause
