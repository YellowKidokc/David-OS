# CODEX START HERE — David-OS Build Orders
**Fabel (Opus) | 2026-07-07 | Master prompt. Read this whole file before touching any code.**

## Who you are in this system
You are Codex, the builder. Opus (Fabel) architects and reviews; David owns the vision
and gives final approval. You do not make design decisions — the folder prompts make
them for you. If a prompt is ambiguous, STOP and post the question to Mattermost
town-square (http://192.168.1.93:8065, user codex-cli, creds in
_ARCHIVE_FIS_20260707\tom_fis_api\mattermost\ai-crew-created-users-*.csv).
Never guess on schema, security, or deletion.

## The one law
**Consolidation-by-copying is the failure mode that created nine copies of this codebase.**
You MOVE, MERGE, and DELETE-WITH-TOMBSTONE. You never copy-and-leave. If you find
yourself duplicating a file "temporarily," stop. There is no temporarily.

## Ground truth documents (read in this order)
1. `core\FIS_HUB_ARCHITECTURE.md` — the brain. Module map, data flows, schema, personas.
2. `_PHASE1_INVENTORY.md` — what existed, what was merged, why.
3. `docs\architecture\` — 11 subsystem docs from prior work. `watcher-vs-dossier-worker.md`
   and the least-action-prediction-engine doc are load-bearing.
4. `config\rules\` — the 28POF rule set. Review gates apply to YOUR work too.

## Build order (do not reorder)
| # | Folder | Prompt | Why this order |
|---|--------|--------|----------------|
| 1 | `api\` | api\CODEX_BUILD_PROMPT.md | The db.py three-way merge. EVERYTHING downstream needs one schema. |
| 2 | `watchers\` | watchers\CODEX_BUILD_PROMPT.md | Five implementations -> one control plane. Feeds the hub. |
| 3 | `ahk\` | ahk\CODEX_BUILD_PROMPT.md | Input bridge hardening + response capture design. |
| 4 | `engine\` | inline below | Wire theophysics-fis ensemble to hub job types. |
| 5 | `apps\desk\` | inline below | React app -> canonical api endpoints. |
| 6 | `pipeline\` | inline below | Intake/scoring scripts -> hub job cards. |

After each folder: run its Tests section, commit with message
`codex: <folder> — <what>`, post one-paragraph summary to town-square,
WAIT for Opus review before the next folder. That's the quality gate. No exceptions.

## Inline briefs (folders 4–6, full prompts issued after gate 1–3 passes)
**engine\** — The preference ensemble (6 engines), chi_engine, capability.py, and
rename_planner arrived from theophysics-fis. They currently import nothing from the hub.
Task: expose each as a hub worker (see `api\file_intelligence_hub\workers\` for the
pattern) so jobs of type `chi_score`, `rename_plan`, `capability_scan` execute through
the standard job queue. Do NOT rewrite the engines; wrap them. Kill condition:
`fihub-worker --limit 1` successfully executes one job of each new type.

**apps\desk\** — React frontend from Top-of-Mind. It calls API paths from the old
Top-of-Mind-API layout. Task: audit every fetch/axios call in src\, point them at the
canonical hub (port 10000 default, 2828 for the OpenAI lane), extract the base URL to
one config file. Do NOT restyle anything. Kill condition: app builds (`npm run build`)
and the message wall loads live data from the hub.

**pipeline\** — power_structure_scanner, chat_fat_cutter, chat_topic_segmenter run
standalone. Task: each gets a `--emit-job-card` flag writing the standard job card JSON
(format: X:\01_FRONT_DOOR\_state\job_cards\) so the orchestrator can chain them.
Do NOT change their core logic. Kill condition: each script runs with the flag and the
card validates against the schema in FIS_HUB_ARCHITECTURE.md.

## Hard rules (apply to every folder)
- `D:\DONT TOUCH BOOT UP` — the name is the rule. Read nothing, write nothing, ever.
- `_ARCHIVE_FIS_20260707\` is READ-ONLY reference. Never import from it at runtime.
- Anything touching `storage\db.py`, credentials, or file deletion = post to
  town-square and wait for explicit approval (28POF review gate).
- Every file you create or substantially rewrite gets a header: purpose, date,
  `codex`, and TESTED/UNTESTED status. Untested code must say so.
- No new dependencies without listing them in the town-square summary.
