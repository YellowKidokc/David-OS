@echo off
setlocal

cd /d "%~dp0"

echo File Integrity Monitor - troubleshoot and reinstall
echo Project: %CD%
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    echo Install Python 3.8 or newer from https://www.python.org/downloads/
    echo Then reopen this window and run this script again.
    pause
    exit /b 1
)

echo Detected Python:
python --version
echo.

if exist ".venv" (
    echo Removing existing virtual environment...
    rmdir /s /q ".venv"
    if exist ".venv" (
        echo ERROR: Could not remove .venv. Close any running Python windows and try again.
        pause
        exit /b 1
    )
)

echo Creating fresh virtual environment...
python -m venv ".venv"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    pause
    exit /b 1
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 (
    echo ERROR: Dependency install failed.
    pause
    exit /b 1
)

echo Running startup import check...
".venv\Scripts\python.exe" -c "import tkinter; import watchdog; import gui; print('Import check passed.')"
if errorlevel 1 (
    echo ERROR: Import check failed.
    pause
    exit /b 1
)

echo.
echo Reinstall complete.
choice /c YN /m "Start File Integrity Monitor now"
if errorlevel 2 (
    exit /b 0
)

call "%~dp0start.bat"
exit /b %ERRORLEVEL%
