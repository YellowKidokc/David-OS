# CODEX BUILD PROMPT — watchers
## Location: D:\GitHub\David-OS\watchers

## Current State
Five watcher implementations, one design doc that already settled the argument:
1. `global-watcher\unified_global_watcher.py` (July 7, 13KB) — newest, multi-root, David-OS native
2. `..\continuous-scanner\continuous_scanner.py` (July 7) — periodic full-scan companion
3. `_candidates\hub_watcher.py` (July 3, 14KB, from tom_fis_api) — HAS TESTS, hub-job-card native
4. `_candidates\legacy_fis_watcher.py` (June 3) — oldest; check for logic the others dropped
5. In-package: `api\file_intelligence_hub\watchers\{native,runner,event_normalizer}.py` — the hub's own intake
Design doc: `docs\architecture\watcher-vs-dossier-worker.md` — READ FIRST. It draws the
line: watchers OBSERVE and emit normalized events; workers ACT. Do not blur it.

## What Works (don't touch)
- The in-package hub watchers (#5). They are the DESTINATION interface, not a candidate.
- X:\01_FRONT_DOOR\_front_door\process_inbox.py — the pipeline intake. Separate layer. Leave it.

## What Needs Combining — THE JOB
Candidates 1–4 become ONE module: `watchers\control_plane.py`.
- Event model: adopt the hub's `event_normalizer` schema (import it; don't reinvent).
- From #1 keep: multi-root config, the drive-letter resilience handling.
- From #2 keep: scheduled full-scan reconciliation (catches events missed while down).
- From #3 keep: job-card emission + its tests (port tests to the new module).
- From #4 keep: nothing unless diff reveals unique handling — document what you checked.
Config: one `watchers\watch_config.json` — roots, ignore globs, scan interval, hub URL.
After merge: candidates 1–4 move to `watchers\_superseded\` with a tombstone note in each.

## What Needs Rewriting
Whatever survives must use watchdog (already a hub dependency) — no polling loops
except the reconciliation scan.

## What Needs Building
`control_plane.py --status` subcommand: prints watched roots, events/hour, last
reconciliation, hub connectivity. One screen, human-readable.

## Dependencies
- Needs: api\ prompt DONE first (unified schema for job cards).
- Feeds: the hub job queue; the orchestrator; eventually the knowledge graph delta feed.

## Tests — kill condition
```
python watchers\control_plane.py --status          # clean output, hub reachable
pytest watchers\tests\ -x                            # ported hub_watcher tests green
# live fire: create/modify/delete a temp file under a watched root ->
# three normalized events appear as hub jobs within 5s, verified via hub API
```
DONE = above green + tombstones placed + town-square summary of what each candidate contributed.

## Priority
Read the design doc, then the event model, then merge. Status command last.
