# file-intelligence-hub

A local control-plane for file-first automation. The hub observes file activity, turns meaningful work into durable SQLite jobs, runs deterministic workers first, and gates risky actions through review before workers mutate files.

## Layers

- `api/`: thin FastAPI routes and app assembly.
- `core/`: orchestration and review gates.
- `storage/`: SQLite schema, migrations, and repositories.
- `workers/`: deterministic job execution such as hashing, classification, rename, and folder summaries.
- `watchers/`: native and polling filesystem event intake.
- `intelligence/`: canonical file facts and compressed folder pattern builders.
- `services/`: operational node health and safe repair logic.
- `config/` and `rules/`: centralized policy inputs; watched folders do not contain local scripts.
- `docs/top-of-mind/` and `config/top_of_mind/`: multi-agent relay notes and source/folder/wall setup for AI, clipboard, and MCP-style controls.

## Local commands

```bash
fihub-api --host 127.0.0.1 --port 10000
fihub-watch --profiles config/folder_profiles.json
fihub-poll --profiles config/folder_profiles.json --once
fihub-worker --limit 1
fihub-health --db .data/file-intelligence-hub.sqlite3
```

## Top of Mind API

The Top of Mind relay lives under `/top-of-mind` and gives other programs one API lane for registering sources, posting messages, pinning/moving items, combining selected messages, and stopping active sources.

See `docs/top-of-mind-api-blueprint.md` for the full API brain map: hub routes, desktop bridges, memory/vectorization, file operators, integrations, and security rules.

## Packaging note

The package discovery is intentionally constrained to `file_intelligence_hub*` so top-level support directories such as `config/` and `schemas/` are shipped as data files instead of being mistaken for import packages.


## Local and LAN startup handoff

### Install and test

```bash
cd apps/api
python -m pip install -e .
python -m pytest
```

### Local-only API startup

Local development can run without a token when bound to loopback only:

```bash
cd apps/api
export FIHUB_DB_PATH=".data/file-intelligence-hub.sqlite3"
fihub-api --host 127.0.0.1 --port 10000
```

OpenAPI is available at:

```text
http://127.0.0.1:10000/openapi.json
http://127.0.0.1:10000/docs
```

### LAN/server-mode API startup

Do not expose this API publicly. For LAN mode, bind to `0.0.0.0` and set a shared token with `FIHUB_API_TOKEN` before startup. Keep the token in your shell, an ignored `.env`, Windows Credential Manager, or a future vault; do not commit it.

```bash
cd apps/api
export FIHUB_DB_PATH=".data/file-intelligence-hub.sqlite3"
export FIHUB_API_TOKEN="replace-with-a-long-random-token"
fihub-api --host 0.0.0.0 --port 10000
```

LAN clients should call the machine IP, for example:

```text
http://192.168.2.50:10000/docs
http://192.168.2.50:10000/jobs
```

Protected API calls accept either `Authorization: Bearer <token>` or `X-API-Token: <token>`.

### Sample curl calls

```bash
curl http://127.0.0.1:10000/openapi.json
curl -H "Authorization: Bearer $FIHUB_API_TOKEN" http://127.0.0.1:10000/jobs
curl -H "Authorization: Bearer $FIHUB_API_TOKEN" "http://127.0.0.1:10000/files/cache/search?q=notes"
curl -X POST -H "Authorization: Bearer $FIHUB_API_TOKEN" -H "Content-Type: application/json" \
  http://127.0.0.1:10000/operator/file-actions \
  -d '{"action":"write_text","target_path":"/tmp/top-of-mind-smoke.txt","text":"hello","review_required":true}'
```

### Sample PowerShell calls

```powershell
cd apps/api
$env:FIHUB_DB_PATH = ".data/file-intelligence-hub.sqlite3"
$env:FIHUB_API_TOKEN = "replace-with-a-long-random-token"
fihub-api --host 0.0.0.0 --port 10000
```

In another PowerShell window:

```powershell
$headers = @{ Authorization = "Bearer $env:FIHUB_API_TOKEN" }
Invoke-RestMethod http://127.0.0.1:10000/openapi.json
Invoke-RestMethod http://127.0.0.1:10000/jobs -Headers $headers
Invoke-RestMethod "http://127.0.0.1:10000/files/cache/search?q=notes" -Headers $headers
Invoke-RestMethod http://127.0.0.1:10000/operator/file-actions -Method Post -Headers $headers -ContentType "application/json" -Body '{"action":"write_text","target_path":"C:\\Temp\\top-of-mind-smoke.txt","text":"hello","review_required":true}'
```

### SQLite path

The default SQLite path is `.data/file-intelligence-hub.sqlite3` relative to `apps/api` when commands are run from that directory. Override it with `FIHUB_DB_PATH`.

### Next endpoint set

Current routes already cover parts of this plan: `/folders`, `/files/cache/search`, `/memory/search`, `/operator/file-actions`, and `/operator/commands`. Next additions should preserve the existing architecture and add thin FastAPI routes backed by SQLite repositories and reviewed worker jobs where mutations are risky:

- `POST /folders/register`
- `POST /folders/scan`
- `GET /files/search`
- `GET /files/read`
- `POST /files/write`
- `POST /files/move`
- `POST /files/copy`
- `POST /files/archive`
- `POST /tags/apply`
- `POST /memory/index`
- `GET /memory/search` improvements for real vector embeddings
- `POST /agents/route`
- `POST /commands/run`
