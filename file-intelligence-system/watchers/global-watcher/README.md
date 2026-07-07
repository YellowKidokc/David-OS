# Global watcher + inspect request service

This folder gives you a single, low-noise watcher that:
- scans configured roots recursively (files + folders)
- writes inspect jobs as simple JSON files (easy for any worker to read)
- accepts manual inspect requests from other programs/scripts
- continuously updates destination jobs without heavy polling

## Files

- `config.example.json` ? runtime settings and roots/ignore lists.
- `unified_global_watcher.py` ? event + periodic scanner.
- `request_file_inspect.py` ? CLI writer for manual inspect requests.
- `start_global_watcher.ps1` ? start the watcher in background.
- `request_file_inspect.bat` ? quick request helper.

## How to run

```powershell
cd "D:\GitHub\David-OS\file-intelligence-system\watchers\global-watcher"
Copy-Item config.example.json config.json
powershell -ExecutionPolicy Bypass -File .\start_global_watcher.ps1
```

## How to ask it to inspect a file right now

```powershell
cd "D:\GitHub\David-OS\file-intelligence-system\watchers\global-watcher"
python request_file_inspect.py "D:\\Users\\David\\Documents\\some.docx" --reason "manual-review"
```

This puts a request file under `jobs\inspect_requests`; watcher will convert it into an inspect job in `jobs\incoming`.