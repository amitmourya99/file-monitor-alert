@echo off
echo ==================================================
echo Compiling File Monitor to Standalone EXE
echo ==================================================

:: Check if pyinstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo Running PyInstaller compile...
pyinstaller --noconsole --onefile --add-data "files/app_icon.png;files" --icon="files/app_icon.png" --name="FileMonitor" files/main.py

if %errorlevel% equ 0 (
    echo ==================================================
    echo SUCCESS: FileMonitor.exe is built inside "dist" folder!
    echo ==================================================
) else (
    echo ==================================================
    echo ERROR: Compilation failed!
    echo ==================================================
)
pause
