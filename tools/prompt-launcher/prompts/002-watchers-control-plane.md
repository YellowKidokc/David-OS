# Prompt 002: Watcher Control Plane

Target: coding
Push target: `git push origin HEAD:codex/watchers-control-plane`

You are working in `D:\GitHub\David-OS`.

Start from a checkout that contains the API foundation branch with:

- schema version 13
- `capability_registry`
- `GET /nodes/status`
- `GET /nodes/capabilities`
- `GET /nodes/capabilities/{capability}/nodes`
- `POST /jobs/help-requests`

If those are missing, stop and report "API foundation missing; wrong checkout."

Read first:

1. `CODEX_START_HERE.md`
2. `watchers\CODEX_BUILD_PROMPT.md`
3. `docs\architecture\watcher-vs-dossier-worker.md`
4. `api\docs\watchers\hub-watcher.md`
5. `api\file_intelligence_hub\watchers\event_normalizer.py`
6. `api\file_intelligence_hub\api\routes_nodes.py`
7. `api\file_intelligence_hub\api\routes_jobs.py`

Hard rules:

- Do not read or modify `D:\DONT TOUCH BOOT UP`.
- Treat `D:\GitHub\_ARCHIVE_FIS_20260707` as read-only reference only.
- Watchers observe and emit normalized events. Workers act.
- Do not build NLP, OCR, tagging, or AI logic inside the watcher.
- If the watcher cannot inspect something, it must create a `help_request` job through the API.
- Keep existing API contracts intact.
- Do not remove `_MERGE_CONFLICTS` unless the full API test suite can pass in the environment.

Task:

Build `watchers\control_plane.py` as the one David-OS watcher control plane.

Use the existing candidates:

- Keep multi-root config and drive-letter resilience from `watchers\global-watcher\unified_global_watcher.py` if present.
- Keep scheduled reconciliation/full-scan behavior from the continuous scanner.
- Keep hub job-card emission patterns and tests from `watchers\_candidates\hub_watcher.py`.
- Check `watchers\_candidates\legacy_fis_watcher.py` for any unique behavior; document what was kept or rejected.
- Use the hub event normalizer instead of inventing a new event schema.

Required behavior:

1. `watchers\control_plane.py --status`
   Prints watched roots, hub URL, node id, events/hour, last reconciliation, and hub connectivity.

2. Node heartbeat
   On startup, register/heartbeat to the API as a watcher node with capability `watch_files`.

3. Normalized event emission
   File create/modify/delete events should become normalized hub events or jobs using the canonical API contract.

4. Help requests
   If a file/folder cannot be read, classified, parsed, or needs NLP/OCR/tagging, create a queued `help_request` job with:
   - `requested_capability`
   - `source_node_id`
   - `file_path` or `folder_path`
   - `reason`
   - `payload`
   - `status: queued`

5. Config
   Add `watchers\watch_config.json` with roots, ignore globs, scan interval, node id, and hub URL.

6. Superseded candidates
   After the new control plane works, move candidate watcher implementations into `watchers\_superseded\` with tombstone notes explaining where their useful behavior went.

Tests / kill condition:

- `python watchers\control_plane.py --status`
- Port or add watcher tests under `watchers\tests\`
- `pytest watchers\tests\ -x`
- If possible, run a live temp-folder test: create, modify, delete a file and verify normalized events/jobs reach the hub.

Deliver:

- Files changed
- What each old watcher contributed
- New config shape
- Example watcher heartbeat payload
- Example help_request payload
- Test results
- Remaining risks

Commit message:

`codex: watchers - consolidate control plane`

Push at the end:

`git push origin HEAD:codex/watchers-control-plane`
