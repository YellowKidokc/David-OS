# Unified File Intelligence Launch Notes

## Stage 0: choose implementation

- `legacy-fis` = classic full pipeline, broad NLP and renamer feature set
- `fihub-source` = modern control-plane with clean API/jobs + folder-based rules

## Quick launch map

1) Legacy route
- `cd D:\GitHub\David-OS\file-intelligence-system\legacy-fis`
- `python -m fis --help`

2) Hub route
- `cd D:\GitHub\David-OS\file-intelligence-system\fihub-source`
- Create/install package per `README.md`
- Start API/worker/watcher from package entrypoint

## Merge strategy (manual)

Do not remove either source. The CORTEX folder layout keeps both and lets you:
- use `fihub-source` as the default staged controller
- use `legacy-fis` when a script dependency expects legacy modules

Use this folder as the single intake location so future scripts can assume:
- `file-intelligence-system/legacy-fis`
- `file-intelligence-system/fihub-source`## Continuous low-resource scanner
- Folder: `continuous-scanner/` (event-driven + batched sync to drive).
- Start with: `powershell -ExecutionPolicy Bypass -File .\start_continuous_scanner.ps1` (run from that folder).
- Use `config.example.json` as your schema and copy to `config.json` for live settings.
