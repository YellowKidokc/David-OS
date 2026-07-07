@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Local virtual environment not found.
    echo Run troubleshoot_reinstall.bat to install the program dependencies.
    pause
    exit /b 1
)

echo Starting File Integrity Monitor...
".venv\Scripts\python.exe" "gui.py"
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo The program exited with code %APP_EXIT%.
    echo Run troubleshoot_reinstall.bat if startup failed.
    pause
)

exit /b %APP_EXIT%
