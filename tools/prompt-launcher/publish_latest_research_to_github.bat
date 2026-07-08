@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%publish_latest_research_to_github.ps1" %*
exit /b %ERRORLEVEL%
