# POF Hub Integration Plan

Source reviewed:

```text
\\192.168.2.50\h_hp\Desktop\pof_hub_integration_plan.html
```

This is the corrected TOP AI FIS version of that plan. The HTML file has the
right architecture instincts, but some filenames and status claims belong to
earlier branches or parallel builds. This document maps the plan to what exists
in this repo now.

## Current Reality

| Area | Current TOP AI FIS file(s) | Status | Notes |
| --- | --- | --- | --- |
| Hub API shell | `apps/api/file_intelligence_hub/api/app.py` | Built | FastAPI app includes jobs, commands, file actions, file cache, folders, intelligence, memory, nodes, semantic, and Top of Mind routes. |
| Top of Mind relay | `routes_top_of_mind.py` | Built | Sources, messages, combine, controls, folders. |
| Clipboard/memory | `routes_memory.py`, `routes_top_of_mind.py` | Partial | Memory route exists. Clipboard save is currently represented through Top of Mind/message flows and imported AHK bridge contracts; dedicated clipboard routes are still a gap. |
| File drop/file actions | `routes_file_actions.py`, `routes_file_cache.py` | Partial | Current repo has proposals/cache, not a dedicated `routes_file_drop.py`. File intake should use cache + jobs + semantic scoring first. |
| Semantic addressing | `routes_semantic.py`, `services/semantic_addressing.py`, `agents/labelers/semantic_addressing/*` | Built | Legacy FIS scorer is now callable through `POST /semantic/score`. |
| Folder scanner | `agents/scanners/folder_scanner.py`, `scan_report.py` | Built/imported | Needs scanner-to-job bridge before it becomes operational control plane. |
| Job system | `core/job_manager.py`, `routes_jobs.py`, `storage/job_repo.py` | Built | Needs more job type coverage and scheduler wiring. |
| Workers | `apps/api/file_intelligence_hub/workers/*` | Partial | Several workers exist: classify, hash, rename, embedding, command, file action, folder summary, review. Need job registry alignment. |
| Review gates | `core/review_gate.py`, `config/rules/review_gates.28pof.v1.json` | Built/partial | Gate rules imported from workbook; need full enforcement across every risky worker. |
| Folder profiles | `config/rules/folder_profiles.28pof.v1.json`, `apps/api/config/folder_profiles.json` | Built/partial | Profiles exist; need profile engine to enforce per-folder automation levels. |
| SQLite schema | `docs/schemas/hub_schema.sql`, `storage/db.py` | Partial but real | Current DB has working tables for jobs, records, cache, memory, routes, folders, nodes. It is not the 44-table workbook target yet. |
| React cockpit | `integrations/top-of-mind-source/apps/desk` | Imported | Needs endpoint alignment and eventual promotion to `apps/web`. |
| AHK bridge | `integrations/ai-hub-v2-source`, `apps/api/scripts/autohotkey/top_of_mind_bridge.ahk` | Imported/partial | AHK can be API hand; needs final hotkey map and route reconciliation. |
| NLP/CHI | `agents/labelers/chi_pipeline.py`, `semantic_addressing/*` | Built/imported | spaCy/Ollama can feed this layer later; deterministic scorer works now. |

## Immediate Wiring Order

The immediate win is not another broad rebuild. It is connecting the existing
pieces into one path:

```text
file event or file cache entry
  -> hash/classify
  -> semantic score
  -> SQLite record
  -> review gate
  -> proposal or safe job
  -> React/AHK approval surface
```

### 1. File Intake To Semantic Score

Add a post-intake hook for file-cache or file-action jobs:

```text
file path -> /semantic/score -> file_records.ai_json or deterministic_json
```

This uses the promoted legacy FIS scorer. No external AI call required.

### 2. Scanner To Jobs

Create a bridge that turns scanner symptoms into jobs:

```text
folder_scanner result
  -> symptom code
  -> severity
  -> suggested job type
  -> review gate decision
```

Examples:

| Symptom | Job candidate | Default action |
| --- | --- | --- |
| duplicate cluster | `duplicate_review` | proposal only |
| extension swamp | `folder_health_scan` | report/proposal |
| program-root danger | `protect_folder` | block automation |
| media dump | `split_folder_proposal` | proposal only |
| huge image/audio/video | `conversion_candidate` | create-copy proposal |

### 3. Folder Profile Enforcement

Every folder must resolve to a profile before any action proposal:

```text
folder path -> profile -> allowed actions + blocked actions + review gates
```

The profile decides whether rename, move, copy, convert, archive, or delete can
even be proposed.

### 4. Review Gate Enforcement

Review gates must become the safety wall between intelligence and action:

```text
worker suggestion -> review_gate -> auto_allow | review_required | blocked
```

Delete, bulk rename, protected folders, program roots, sensitive files, and low
confidence actions should default to review or block.

### 5. React/AHK Approval Surface

React is the cockpit. AHK is the desktop hand. Neither should be the source of
truth.

```text
React: inspect, approve, reject, route
AHK: paste, send, hotkeys, active-window control
Hub: storage, permissions, review gates, jobs
```

## Evaluation Framework

The system needs to measure whether it is improving.

### Scanner Evaluation

| Metric | Question | Target |
| --- | --- | --- |
| Precision | Of symptoms flagged, how many are real? | >90% on known-clean folders |
| Recall | Of seeded problems, how many are caught? | >90% on test folders |
| Grade accuracy | Does folder grade match human judgment? | Within one grade 90% of time |
| Delta reliability | Does score improve when symptoms are fixed? | Positive proportional movement |

### Semantic Classification Evaluation

| Metric | Question | Target |
| --- | --- | --- |
| Cross-AI agreement | Do AIs agree on dominant semantic variables? | Keep old 85-90% baseline |
| Hash predictability | Can a hash predict broad content family? | >80% domain accuracy |
| Coverage | Does every meaningful file get non-empty signal? | Minimize all-zero results |

### Rename/Action Evaluation

| Metric | Question | Target |
| --- | --- | --- |
| Accept rate | Does David accept suggestions without edits? | >70% after learning |
| Edit distance | How much must suggestions be corrected? | Trend downward |
| Breakage | Did a suggestion break code/links/imports? | Zero tolerance |
| Review burden | Are reviews faster than manual organizing? | Yes, visibly |

## Intelligence Levels

### Level 1: Deterministic

Use file extension, path, folder profile, timestamps, hashes, sidecars, and known
program-root markers. This is cheap and should do most first-pass work.

### Level 2: Local AI

Use Ollama or local NLP for rename suggestions, folder summaries, tag inference,
and duplicate tiebreak explanations.

### Level 3: Memory/Preference Learning

Every accepted/rejected suggestion becomes a signal. Store it in SQLite and
learn folder-specific preferences.

### Level 4: Agent Coordination

Claude, Gemini, Codex, Kimi, GPT, Operator, and Clipboard communicate through
the hub, not through fragile copy/paste alone.

## Build Queue

| Order | Work item | Why next |
| --- | --- | --- |
| 1 | File-cache semantic post-hook | Connects the old scorer to current intake. |
| 2 | Scanner-to-jobs bridge | Turns reports into operational work. |
| 3 | Folder profile policy engine | Prevents dumb automation in dangerous folders. |
| 4 | Review gate enforcement pass | Makes safety consistent. |
| 5 | Dedicated clipboard routes | Closes the AHK/clipboard gap cleanly. |
| 6 | React review queue panel | Lets David approve/reject quickly. |
| 7 | AHK route reconciliation | Makes hotkeys call stable hub endpoints. |
| 8 | Preference learner v1 | Starts learning from corrections. |

## Corrected Takeaway

The HTML plan is right about the direction:

```text
watchers + scanner + semantic scorer + jobs + review gates + memory + React/AHK
```

But the repo is already further along in some places and less complete in
others. The next concrete target should be:

```text
File cache/intake calls /semantic/score and stores the result in SQLite.
```

That makes the old FIS semantic breakthrough part of the living hub.
