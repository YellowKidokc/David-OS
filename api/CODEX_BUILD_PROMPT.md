# CODEX BUILD PROMPT — api
## Location: D:\GitHub\David-OS\api

## Current State
The assembled three-way merge. `file_intelligence_hub\` is HEAD-D (tom_fis_api, July 3–5)
plus rescued unique files that were MOVED IN but are NOT YET WIRED:
- `api\routes_clipboard.py`, `api\routes_agents.py`, `storage\clipboard_repo.py` (from Synology stage, "HEAD-F")
- `api\routes_semantic.py`, `services\semantic_addressing.py` (from TOP AI FIS, "HEAD-G")
- `scripts\folder_agent.py`, `scripts\remote\*.ps1`, `tests\test_clipboard.py`, `tests\test_remote_auth.py`
Working HEAD-D core: app assembly, routes_openai_compat (LIVE on port 2828 serving
Mattermost), routes_prediction + prediction_engine, routes_folders, security.py,
numbering schema, full test suite, SQLite migrations in `storage\db.py`.

## What Works (don't touch)
- `api\routes_openai_compat.py` — in production tonight. Do not modify its contract.
- `core\`, `workers\`, `watchers\`, `intelligence\` — HEAD-D internals, untouched this pass.
- `security.py` and the review-gate logic.

## What Needs Combining — THE JOB
Three divergent versions of two files, parked at `D:\GitHub\David-OS\_MERGE_CONFLICTS\`:
- `F\file_intelligence_hub\storage\db.py` + `F\...\api\app.py` (clipboard/agents era)
- `G\file_intelligence_hub\storage\db.py` + `G\...\api\app.py` (semantic era)
- Base: the live `api\file_intelligence_hub\storage\db.py` and `api\app.py` (HEAD-D)

**db.py**: Diff each of F and G against base. Each adds tables/columns the base lacks
(F: clipboard storage tables; G: semantic addressing tables). Produce ONE db.py where
F and G additions become NEW numbered migrations appended AFTER the base's migration
chain — never renumber or edit existing migrations; existing hub databases must upgrade
in place. Output file: overwrite `api\file_intelligence_hub\storage\db.py`.
**app.py**: Base assembly + register routes_clipboard, routes_agents, routes_semantic
alongside existing routers. Match base's include_router style exactly.
When both are merged, DELETE the `_MERGE_CONFLICTS\` folder (git preserves history).

## What Needs Rewriting
Nothing in this pass. Merge only. Resist improvement urges.

## What Needs Building
Nothing new. This prompt is 100% reconciliation.

## Dependencies
- Downstream: EVERY other folder prompt assumes this schema is unified. This is prompt #1 for a reason.
- Upstream: none. Self-contained.

## Tests — kill condition
```
cd D:\GitHub\David-OS\api
python -m pytest tests\ -x         # full suite green, including test_clipboard + test_remote_auth
python -c "from file_intelligence_hub.storage.db import *"  # imports clean
# fresh db builds all migrations:
python -m file_intelligence_hub.cli init --db .data\merge_test.sqlite3
# live server still boots and /v1/models still answers:
python -m uvicorn file_intelligence_hub.api.app:create_app --factory --port 2829
curl http://localhost:2829/v1/models
curl http://localhost:2829/clipboard/health   (or the route's actual health path)
```
DONE = all of the above green + one town-square post listing every schema change made.

## Priority
db.py first. app.py second. Nothing else.
