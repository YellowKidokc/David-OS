@echo off
setlocal

set "RESEARCH_URL=%~1"
if "%RESEARCH_URL%"=="" set "RESEARCH_URL=https://gemini.google.com/app/5066cf74c5e36b8d"

set "SCRIPT_DIR=%~dp0"
set "DOCS_FLAG="
if /I "%~2"=="--docs" set "DOCS_FLAG=--docs"
if /I "%~3"=="--docs" set "DOCS_FLAG=--docs"

node "%SCRIPT_DIR%export_gemini_research.mjs" "%RESEARCH_URL%" %DOCS_FLAG%
exit /b %ERRORLEVEL%

