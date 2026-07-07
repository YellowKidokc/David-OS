# Low-resource continuous scanner

Copy this folder into your CORTEX run flow:

- Edit config before first run
  - `D:\GitHub\David-OS\file-intelligence-system\continuous-scanner\config.example.json`
- Duplicate config as `config.json` (the service reads `config.json`)
- Start with PowerShell:

```powershell
cd "D:\GitHub\David-OS\file-intelligence-system\continuous-scanner"
cp config.example.json config.json
powershell -ExecutionPolicy Bypass -File .\start_continuous_scanner.ps1
```

## What it does

- Continuous, event-driven file watching (watchdog)
- Debounces duplicate events (low noise)
- Batches writes and syncs updates to the mapped target drive
- Keeps runtime state in `run/state.json` so resumes are fast
- Does no full-tree scan by default

## Resource controls

- `scan_interval_seconds`: how often the writer flushes batches
- `dedupe_seconds`: collapses duplicate file save bursts
- `batch_limit`: upper bound files processed per flush
- `max_file_size_bytes`: skip large files from immediate sync
- `fallback_full_scan_hours`: optional deep safety scan interval (0 = off)

For very low CPU/RAM, keep watch roots narrow and use ignore roots heavily.

## Current defaults

- Target drive sync path: `O:\\CORTEX-FIS-Drive`
- Watch root example: `C:\\Users\\David\\Documents`
- Ignore AppData, Temp, and common churn paths by default

## Minimal stop behavior

Stop: close Python process from Task Manager or stop the powershell host.

This is intentionally non-destructive and can run in parallel with your existing
legacy `fis` and `file-integrity-monitor` paths.