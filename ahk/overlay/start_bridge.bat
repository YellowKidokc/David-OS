@echo off
REM start_bridge.bat - launch listener + overlay together
start "bridge-listener" powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0bridge_listener.ps1"
start "" "%~dp0ai_input_overlay.ahk"
echo Bridge started. Overlay on screen, API on port 8765.
echo Test:  curl -X POST http://localhost:8765/send -H "X-Bridge-Token: davidos-bridge-2026" -H "Content-Type: application/json" -d "{\"text\":\"hello from the bridge\",\"enters\":1}"
