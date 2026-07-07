# Next Build Handoff

## Current State

The TOP AI FIS folder now has the first hub layout.

Working scanner/report files have been copied into:

- `agents/scanners/folder_scanner.py`
- `agents/scanners/scan_report.py`

The initial SQLite schema is:

- `docs/schemas/hub_schema.sql`

## Next Tasks

1. Add a small bootstrap script that creates `data/sqlite/fis_hub.sqlite`.
2. Add a FastAPI skeleton in `apps/api`.
3. Add `/health`, `/nodes/heartbeat`, `/events/file`, `/scan/folder`, `/clipboard/save`.
4. Connect `agents/scanners/folder_scanner.py` to `/scan/folder`.
5. Add read-only watcher prototype in `agents/watchers`.
6. Import existing AutoHotkey bridge references into `integrations/autohotkey`.

