# PHASE 1 INVENTORY — FIS / Top-of-Mind Consolidation
**Fabel (Opus) | July 7, 2026 | Read-only pass. Nothing built, nothing moved.**
Raw data: `_PHASE1_FILELIST.txt` (3,830 entries, 8 roots) + `_phase1_hash_audit.py` (MD5 verification, run 2026-07-07)

---

## 1. THE HEADLINE

The `file_intelligence_hub` Python package exists in **NINE locations** resolving to **FIVE distinct versions**.
Hash-verified identity groups:

| Group | Copies | Status |
|---|---|---|
| **STALE-4** (byte-identical) | `File-intelligent-hub\file-intelligence-hub`, `David-OS\...\fihub-source`, `David-OS\...\segments\01-core...`, `TOP AI FIS\integrations\file-intelligent-hub-source` | July 2 snapshot. Archive all four. |
| **HEAD-D** | `tom_fis_api\apps\api` | Newest (July 3–5). UNIQUE: `routes_openai_compat.py`, `routes_api_actions.py`, `api_action_registry.py`, prediction engine, hub_watcher tests. |
| **HEAD-E** (×2 identical) | `Top-of-Mind-API\apps\api` + its vendored mirror in `TOP AI FIS\integrations\top-of-mind-api-source` | July 2–3. No unique .py files vs heads, but owns the Synology deploy pipeline (.spk build). |
| **HEAD-F** | `Top-of-Mind-API\deploy\synology\.package-stage\apps\api` | UNIQUE: `routes_clipboard.py`, `routes_agents.py`, `clipboard_repo.py`, `folder_agent.py`, remote auth scripts + tests. Exists NOWHERE else. |
| **HEAD-G** | `TOP AI FIS\apps\api` | UNIQUE: `routes_semantic.py`, `services/semantic_addressing.py` (bridges legacy-fis semantic scorer into the hub). |

**Consequence:** the merge is NOT "pick tom_fis_api, archive the rest." It is a
**three-way feature merge**: HEAD-D as base + cherry-pick clipboard/agents/remote from HEAD-F + semantic routes from HEAD-G.
20 shared files have divergent hashes across heads (full list in hash audit output) — `storage/db.py` differs in THREE ways.

---

## 2. WHAT EACH REPO IS

**David-OS** — intended canon, currently thin + self-duplicating.
- Live/unique: `AI READ.md`, `core\{RUNNER,SCHEMA,SCORING_STANDARD}.md`, `pipeline\` (power_structure_scanner.py + 21MB manifest, chat_fat_cutter, chat_topic_segmenter — all July 6–7), `scoring\auto_scorer.py`, `llm-wiki\init_llm_wiki_db.py`, `watchers\global-watcher\unified_global_watcher.py` (July 7), `continuous-scanner\` (July 7).
- Dead weight: `segments\` mirrors fihub-source, legacy-fis, watchers, continuous-scanner, AND the file-integrity-monitor byte-for-byte. Delete in merge.
- Stale: `fihub-source` (STALE-4 member), `legacy-fis` (dup of file-intelligence-system repo).

**tom_fis_api** — the working head (HEAD-D) + the AHK layer + GUI.
- `apps\api` = canonical API base for the merge.
- `ahk\` = AI Chat Controller v3 lineage + 13 API_CALL prompt files + routing manifest.
- `agents\watchers\hub_watcher.py` (July 3) = newest watcher.
- `GUI\` = ARCHITECTURE.md (June 29) + KIMI modules — not fully cataloged this pass, contains the api-codex-online-wiring module.
- `apps\gui-neighborhood\imports\` = LEGACY GRAVEYARD (ahk_dashboard/Emma from April, three generations of AI-HUB AHK, Physics_of_faith PWA with full shadcn vendor tree). Archive wholesale; do not merge.

**Top-of-Mind-API** — deploy pipeline owner (HEAD-E) + buried treasure (HEAD-F).
- Synology .spk build chain works (dist\TopOfMindAPI-0.1.0-001.spk exists).
- HEAD-F inside `.package-stage` is the ONLY copy of clipboard/agents/remote-auth code. Rescue before archiving this repo.

**Top-of-Mind** — React frontend, two copies of the same app.
- `apps\desk` (main.jsx 24KB, July 3) = live head, includes `docs\ahk-react-api-contract.md` (the AHK↔React↔API contract).
- `frontend\top-of-mind` (main.jsx 4.4KB, July 2) = earlier scaffold. Archive.

**File-intelligent-hub** — origin repo. STALE-4 member + `typingmind\` (vendored third-party app, ~15MB of assets, its own server logs). Archive whole repo; typingmind stays out of David-OS.

**theophysics-fis** — PRIOR consolidation attempt (June 27). Has its own `CONSOLIDATION_SPEC.md` (24KB), `CRITICAL_FIXES.md` (16KB), a clean `src\` engine (capability.py, chi_engine, preference ensemble with 6 engines, rename_planner, ledger), config YAMLs, and `archive\_to_review\` holding filetagger + chi_qi_v5 + corpus_engine + 700MB of .db files. The `src\` engine and both spec docs must be READ before Phase 2 script is final — it already solved parts of this problem.

**TOP AI FIS** — SECOND prior consolidation attempt (July 3), the most architecturally mature:
- `docs\architecture\` — 11 docs incl. hub-overview, scanner-pipeline, least-action-prediction-engine, watcher-vs-dossier-worker, memory-buckets.
- `docs\handoffs\forgotten-systems-inventory.md` — someone already inventoried the forgotten systems. Read it.
- `config\rules\` — the 28POF rule set (symptom registry, review gates, label enforcement, onboarding questions).
- `data\memory\TopOfMind_Memory\` — the agent memory bucket tree (per-AI private + shared).
- `agents\` — labelers (chi pipeline, semantic addressing worker), scanners (folder_scanner 40KB), watchers.
- HEAD-G api + vendored mirrors of four other repos.

**file-intelligence-system** (standalone repo) — the April legacy-fis. Identical content to the two copies inside David-OS. One archived copy survives; the other two die.

---

## 3. THE WATCHER PROBLEM (David flagged this)

Five implementations found:
1. `David-OS\watchers\global-watcher\unified_global_watcher.py` — July 7, newest, 13KB
2. `David-OS\...\continuous-scanner\continuous_scanner.py` — July 7
3. `tom_fis_api\agents\watchers\hub_watcher.py` — July 3, 14KB, has tests
4. `legacy-fis fis\watcher.py` — June 3 (×3 copies)
5. Salvaged: `filetagger_daemon.py` (June 27), `salvaged_file_watcher.py`, file-integrity-monitor `monitor.py` (June 20, ×3 copies)
Plus in-package `watchers\{native,runner,event_normalizer}.py` in every hub copy.
→ Phase 3 watcher prompt = consolidation into ONE control plane (TOP AI FIS `docs\architecture\watcher-vs-dossier-worker.md` already argues the design).

## 4. DEAD / ARCHIVE-ONLY
- All STALE-4 copies; David-OS `segments\` (entire); `gui-neighborhood\imports\` (Emma/ahk_dashboard, three AI-HUB generations, PWA vendor trees); typingmind; `frontend\top-of-mind` scaffold; pytest caches, .sqlite3-wal/shm, service.log (648KB), 700MB of .db in theophysics-fis archive (keep on disk, exclude from repo); duplicate clipboard*.html generations (≥12 variants across trees).

## 5. GAPS
- **Today's ARCHITECTURE.md + FIS_HUB_ARCHITECTURE.md are not on disk.** Only chat downloads. Must land in `David-OS\core\` before Phase 2/3. (power_structure_scanner.py IS already saved.)
- No single canonical README declaring David-OS as canon — `AI READ.md` exists (36KB, July 7) but the five-copy landmine field contradicts it.
- HEAD-F code has zero presence outside a deploy staging folder — one `git clean` away from extinction.

## 6. PHASE 2 MERGE ORDER (input for the script)
1. Freeze: `git commit` all 8 roots as-is (safety tag `pre-consolidation-20260707`).
2. Base: copy HEAD-D → `David-OS\api\`.
3. Cherry-pick: HEAD-F clipboard/agents/remote + tests; HEAD-G semantic + service; resolve the 20 divergent shared files (take HEAD-D except where F/G features require their db.py migrations — needs eyes, not automation, on `storage/db.py`).
4. Absorb: theophysics-fis `src\` engine → `David-OS\engine\`; TOP AI FIS `docs\architecture\` + `config\rules\` + memory buckets → David-OS.
5. Frontend: `Top-of-Mind\apps\desk` → `David-OS\apps\desk\` + the ahk-react contract doc.
6. AHK: tom_fis_api `ahk\` (v3 controller + API_CALLfiles) → `David-OS\bridges\ahk\`.
7. Watchers: all five implementations → `David-OS\watchers\_candidates\` for the Codex consolidation prompt.
8. Archive: everything else → `D:\GitHub\_ARCHIVE_FIS_20260707\` (move, don't delete). Mark tom_fis_api / Top-of-Mind-API / File-intelligent-hub / theophysics-fis / TOP AI FIS / file-intelligence-system with a single ARCHIVED.md pointer to David-OS.
9. Kill David-OS `segments\` + internal fihub-source/legacy-fis dups.

**NOT TOUCHED THIS PASS:** `D:\DONT TOUCH BOOT UP` (per name), `tom_fis_api\GUI\` internals (next read), _tom-kimmy-desk.
