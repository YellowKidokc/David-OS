@echo off
setlocal

set "PROMPT_NAME=%~1"
if "%PROMPT_NAME%"=="" set "PROMPT_NAME=001-deep-research"

set "SCRIPT_DIR=%~dp0"
set "PROMPT_FILE=%SCRIPT_DIR%prompts\%PROMPT_NAME%.md"

if not exist "%PROMPT_FILE%" (
  echo Prompt not found: %PROMPT_FILE%
  echo.
  echo Available prompts:
  dir /b "%SCRIPT_DIR%prompts\*.md"
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-Clipboard -LiteralPath '%PROMPT_FILE%'"
if errorlevel 1 exit /b 1

echo Copied prompt to clipboard:
echo %PROMPT_FILE%
echo.
echo Prompt metadata:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Select-String -LiteralPath '%PROMPT_FILE%' -Pattern '^(Target|Push target|Output target):' | ForEach-Object { $_.Line }"
echo.

if /I "%~2"=="--playwright" goto playwright
if /I "%~3"=="--playwright" goto playwright

echo Paste it into the online tool when ready.
exit /b 0

:playwright
set "SUBMIT_FLAG="
if /I "%~2"=="--submit" set "SUBMIT_FLAG=--submit"
if /I "%~3"=="--submit" set "SUBMIT_FLAG=--submit"

node "%SCRIPT_DIR%launch_prompt.mjs" "%PROMPT_FILE%" %SUBMIT_FLAG%
exit /b %ERRORLEVEL%
