# File Intelligence System (David-OS)

This is the single container for your final intelligence system.

## Segments

Open these directly in order:

- `segments/01-core-intelligence-hub/` ? modern control-plane (`file_intelligence_hub` API, jobs, rules, workers, watchers).
- `segments/02-legacy-fis/` ? full legacy FIS stack (classifier, renamer, DB schemas, NLP, scoring, UI).
- `segments/03-watcher-control-plane/` ? global watcher that discovers files/folders and emits inspect jobs.
- `segments/04-continuous-sync/` ? low-resource continuous sync monitor to drive/backup targets.
- `segments/05-file-integrity-monitor/` ? legacy file-integrity monitor implementation from your existing BOOT UP set.

## Companion folders (legacy snapshots)

- `legacy-fis/` and `fihub-source/` hold source snapshots used to seed the new segment layout.
- `watchers/`, `continuous-scanner/`, and `unified-system/` are legacy-arrangement mirrors kept for compatibility during migration.
- `README.md` files in each segment explain launch and wiring.

## Entry points

- `D:\GitHub\David-OS\fis\README.md` maps here for quick discovery from your existing workflow.
- `segments/03-watcher-control-plane/global/request_file_inspect.py` is the manual "inspect this file now" bridge.
- `segments/03-watcher-control-plane/global/request_file_inspect.bat` for quick invocation.