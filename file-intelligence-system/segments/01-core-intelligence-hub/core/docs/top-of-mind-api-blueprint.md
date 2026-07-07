# Top of Mind API Blueprint

This repo is the API brain for Top of Mind.

It should collect the parts that let AIs, desktop bridges, files, memory, folders, NAS/cloud services, and the frontend talk through one control plane.

## Repo Role

`file-intelligence-hub` owns:

- API routes
- SQLite storage
- job queue
- review/approval flow
- file actions
- command actions
- memory/search
- integration registry
- security rules
- API map and docs

It should not own:

- raw passwords
- large media payloads
- permanent frontend build artifacts
- one-off scripts hidden inside watched folders

## Core API Ranges

| Range | Owns | Current Docs |
| --- | --- | --- |
| Hub Brain APIs | messages, jobs, reviews, nodes, sources | `docs/api-map/README.md` |
| Desktop Bridge APIs | AHK, OCR boxes, typing/clicking apps | `docs/folder-agents/README.md` |
| File and Storage APIs | local files, NAS, Syncthing, R2, WebDAV | `docs/integrations/README.md` |
| Knowledge APIs | memory, tags, future vectors | `docs/memory/README.md` |
| Security | secret refs, review defaults, ledger | `docs/security/README.md` |

## Active API Surface

Top of Mind:

- `GET /top-of-mind/sources`
- `POST /top-of-mind/sources`
- `GET /top-of-mind/messages`
- `POST /top-of-mind/messages`
- `PATCH /top-of-mind/messages/{message_id}`
- `POST /top-of-mind/combine`
- `POST /top-of-mind/controls/end-all`

Memory:

- `POST /memory/items`
- `GET /memory/items`
- `GET /memory/items/{item_id}`
- `GET /memory/search?q=...`

Operators:

- `POST /operator/file-actions`
- `POST /operator/commands`

Existing hub:

- `POST /jobs/file-events`
- `POST /jobs/folder-summaries`
- `GET /jobs`
- `GET /jobs/stats`
- `GET /reviews`
- `POST /reviews/{review_id}/approve`
- `POST /reviews/{review_id}/reject`
- `POST /reviews/{review_id}/defer`
- `GET /nodes`
- `POST /nodes/heartbeat`
- `GET /intelligence/files`
- `GET /intelligence/folders/summary`

## Folders To Keep Together

API code:

- `file_intelligence_hub/api/`

Storage:

- `file_intelligence_hub/storage/`

Workers:

- `file_intelligence_hub/workers/`

Configs:

- `config/top_of_mind/`
- `config/integrations/`
- `config/folder_profiles.json`

Docs:

- `docs/api-map/`
- `docs/folder-agents/`
- `docs/integrations/`
- `docs/memory/`
- `docs/security/`
- `docs/top-of-mind/`

Bridge examples:

- `scripts/autohotkey/`

Frontend:

- `frontend/top-of-mind/` once the frontend branch is pushed or copied into this repo.

## Near-Term Build Order

1. Keep API tests passing.
2. Pull or recreate the React/Vite frontend under `frontend/top-of-mind`.
3. Run the API on LAN, for example `http://192.168.2.50:8000`.
4. Run one AHK bridge profile against one AI input box.
5. Post and retrieve messages through `/top-of-mind/messages`.
6. Use `/operator/file-actions` for Markdown/TXT writes and folder moves.
7. Add memory/vectorization workers after the UI and bridge loop are proven.
8. Add integration connectors for NAS, Syncthing, Cloudflare R2, and WebDAV.

## Security Defaults

- Store `secret_ref`, never raw passwords or tokens.
- Commands and risky file actions should default to review-required.
- Every mutation should create a ledger entry.
- LAN access should be treated as private but not trusted forever.
- Before exposing through Cloudflare, add authentication.

## One-Sentence Architecture

Top of Mind Hub is the brain, React Desk is the face, AutoHotkey/Rust bridges are the hands, and integrations are the arms that reach NAS, cloud, command lines, OCR, and other APIs.
