@echo off
cd /d %~dp0
if not exist config.json copy config.example.json config.json
python request_file_inspect.py %*