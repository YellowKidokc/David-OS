# Theophysics File Intelligence System - Consolidation Spec
## Handoff Document for CLI / Claude 4.8
### POF 2828 | June 27, 2026

---

## ✅ AS BUILT — June 27, 2026 (read this first)

The consolidation was built into a **professional pipeline layout** (`config/` +
`system/` + `src/`) rather than the `core/engines/consumers/sidecars` sketch
below. The spine is **observe → identify → understand → propose**, with a JSONL
event ledger + SQLite inventory and file-identity-by-hash. It is **read-only /
propose-only**: nothing is renamed, moved, or deleted. See `README.md` for usage.

### Module map (what each src/ file is, and what real script it absorbed)

| src/ module | Job | Spliced from |
|---|---|---|
| `config.py` | paths, data model, code tables, YAML loader | new (contract) + `FIS_NAMING_SPEC.md` |
| `fingerprint.py` | sha256 identity, size, mtime, simhash | `file-integrity-monitor\`, corpus scanner |
| `text_extractor.py` | readable text (md/txt/html/pdf/docx) | `chi_qi_v5_metric_engine.read_text` |
| `chi_engine.py` | real χ/Qi v5 scoring engine (copied verbatim) | `chi_qi_v5_metric_engine.py` |
| `chi.py` | thin `score_text()` wrapper over the engine | new |
| `domain_classifier.py` | 5 tags (domain/CT/status/date/slug) + chi profile | `fis_classifier.py`, `filetagger_chi_v2.py`, `domains.yaml` |
| `tagger.py` | topic slug + compressed tag codes | `fis_namer.py` (TAG_ABBREVS) |
| `preference/` (package) | pluggable ensemble of preference engines (River, sklearn-GBDT, Vowpal Wabbit, frequency baseline, MS-Recommenders/LightGBM adapter) with blend/cascade modes + `compare` backtest | `fis_preference_engine.py` + `D:\GitHub\recommenders` |
| `preference_engine.py` | back-compat shim → `preference.get_ensemble()` | — |
| `rename_planner.py` | propose `DOMAIN__CT__tags__date__ST.ext` (propose-only) | `fis_namer.py` (propose_name) |
| `enricher.py` | low-confidence TF-IDF match vs similar files; borrow domain/tags | `fis_enricher.py` |
| `wordnet_expander.py` | WordNet query pre-pass (synonyms + parents) | `filetagger\wordnet_expander.py` |
| `capability.py` | subject-category capability gate; regulated → block_pending + provisioning checklist | user-provided module (verbatim) |
| `category_markov.py` | folder category-Markov: fills `uncategorized` from neighbours | new |
| `preference/markov_engine.py` | two-class Markov sequence classifier (preference engine) | new |
| `metadata_db.py` | SQLite current-state store (path-keyed upsert) | corpus_engine `preference_store`/schema |
| `ledger.py` | append-only JSONL event/rename/error logs | new (pro-doc requirement) |
| `inventory_scan.py` | the pipeline orchestrator + folder symptoms | corpus_engine `run.py`/`folder_scanner.py` |
| `report_builder.py` | approval_queue.csv + rename_plan.html | corpus_engine `excel_preview.py` |
| `cli.py` | scan / report / status / learn commands | corpus_engine `run.py` |

### Comparison: scaffold sketch → real source → what was kept

| Original sketch module | Matching real source(s) | What the source did better | Resolution |
|---|---|---|---|
| `engines/chi_vectors.py` | `chi_qi_v5_metric_engine.py` + lexicon xlsx | real lexicon-driven χ scoring with evidence/fruit | copied engine verbatim, wrapped by `chi.py` |
| `engines/preference.py` | `fis_preference_engine.py` | River SGD LogisticRegression, learns per-decision | spliced near-verbatim → `preference_engine.py` |
| `core/classifier.py` | `fis_classifier.py` / `filetagger_chi_v2.py` | 5-tag (adds content_type + evidence) | rebuilt config-driven in `domain_classifier.py` |
| `core/namer.py` | `fis_namer.py` + `FIS_NAMING_SPEC.md` | compressed grep-able code names | spliced → `rename_planner.py` + `tagger.py` |
| `core/symptoms.py` | `folder_symptom_registry.xlsx` | 20-symptom registry | registry in `config.py`; 6 detectors live in `inventory_scan.py` |

### Verified
- `python -m compileall src` → OK
- `scan --roots ./sample` → 2 files classified, named, CSV+HTML generated
- `scan --roots faiththruphysics-site-data --limit 200 .md .html` → 200 files in 71s;
  domains TH 147 / PH 31 / MD 16 / KG 3 / EV 2 / EP 1; 119 papers; 114 queued / 84 auto;
  11 folders flagged with symptoms; incremental commits confirmed.

### Deliberately deferred (next phases)
`watcher.py`, `event_normalizer.py` (full copy/move inference), vector index + chat
(RAG), and the **apply** worker (executes approved renames with rollback).

### Enricher (wired June 27, 2026)
Low-confidence files (`confidence < 0.50`) now run through `enricher.py`:
WordNet-expand the filename words → TF-IDF char-ngram match against similar
already-classified files → borrow domain + tags. Corpus = approved `filebrain`
rows first (real tag codes), falling back to the 819k-row `chi_catalog_v2.db`
(read-only). `cli.py learn` writes approvals back to the DB so the approved corpus
grows. Outcome + matched file surface in the CSV `context` column.
Readable low-confidence files are no longer `skip`ped — they're queued so the
enricher can rescue them; `skip` is now reserved for unreadable/binary files.

### Multi-engine preference (wired June 27, 2026)
`preference/` runs several learners behind one interface (`base.PreferenceEngine`):
`frequency` (baseline), `river`, `sklearn_gbdt`, `vowpal_wabbit`, and a best-effort
`recommenders_lightgbm` adapter (puts `D:\GitHub\recommenders` on `sys.path`; lights
up when `lightgbm` is installed). `config/engines.yaml` sets which are enabled,
their blend weights, and the mode (`blend` weighted-average, or `cascade` =
first-confident-engine-wins / "wire one into another"). `learn` trains them all and
logs every decision; `cli.py compare` backtests them prequentially and ranks by
warm-up accuracy + logloss. Verified contest (40 learnable decisions): sklearn_gbdt
0.96 / vowpal_wabbit 0.93 / river 0.90 / frequency 0.78 warm accuracy. Adding an
engine = one file + a registry line.

### Capability gate + Markov (wired June 27, 2026)
`capability.py` (dropped in verbatim, passes its own smoke test) runs after naming:
scores subject category, assigns an access tier, and routes each file —
`process_deep/local/shallow`, `review`, or `block_pending` for regulated
(medical/legal/financial) data with no provisioned source. Fail-safe: a near-top
regulated category wins. Policy in `config/capability.json`. The scan prints a
provisioning checklist; DB gets `gate_category/gate_tier/gate_route/gate_access`.

Markov chains, two placements:
1. `category_markov.py` — folder category-Markov fills `uncategorized` files from
   `P(category | previous-file-category)` (verified: `PowerShellCommander.ahk`
   uncategorized → `technical_software` from its AHK neighbours).
2. `preference/markov_engine.py` — a two-class Markov sequence classifier joins the
   ensemble and **won the backtest**: warm accuracy markov 1.00 / sklearn_gbdt 0.96
   / vowpal_wabbit 0.93 / river 0.90 / frequency 0.78.

Also fixed: `learn` no longer clobbers system-stamped notes — it appends `[user]`
notes and preserves the `[GATE …]` / `[enriched]` stamps.

### Known tuning notes
- `.md`-type files are "ext-certain" so they show `decision=auto_approve` even at
  low confidence (faithful to `fis_namer`); since nothing is ever applied this is
  advisory only, but you may want low-confidence files forced to `queue` instead.
- Per-file χ scoring is the throughput cost (~3 files/sec). Fine for batch review;
  for full-drive bulk runs, cap units or memoize. Periodic commit makes long scans
  resumable.
- Enricher strong-match (`enriched`, sim ≥ 0.60) is rare against the generic
  reference catalog with char-ngram filename matching; it sharpens as the approved
  corpus grows. `compare`/`uncertain` outcomes still queue with context.

---

### (Original handoff sketch below — kept for history; the AS-BUILT map above supersedes it.)

---

## SCOPE — READ THIS FIRST

**This system is ONE component. It is a file name classifier and database store.**

Specifically, it does three things:
1. **Scans** files and reads their metadata
2. **Classifies** them — assigns domain, chi factor, law, content type, evidence tag
3. **Proposes** a canonical file name using the FIS naming scheme
4. **Stores** everything in SQLite for review

It does NOT:
- Move or rename files (that is a separate executor component, built later)
- Clean up folders or reorganize directory structure (later)
- Constitute a full intelligence system (that comes after this foundation is solid)

The approval queue + Excel review step exists so a human stays in control.
Nothing touches the actual files until explicitly approved and a separate
executor component is built and wired in. **This is a read-only classifier
that proposes actions. That is all it needs to be right now.**

The full File Intelligence System — decision engine, relationship graph,
automated executor, cross-file reasoning — is a later phase built on top
of this foundation once the classification layer is trusted and the database
is populated.

---

## MISSION
Consolidate all scattered file management scripts into ONE folder:
`D:\GitHub\theophysics-fis\`

Deduplicate, archive old versions, produce clean corporate-grade Python.
Log everything to SQLite. Excel preview for human review. Preference
engines for learning. API fallback for deep classification.

---

## EXISTING PIECES TO CONSOLIDATE

### 1. Filetagger Suite
**From:** `D:\DONT TOUCH BOOT UP\filetagger\`
- `filetagger_chi_v2.py` - chi-factor classifier (LATEST)
- `chi_pipeline.py` - classification pipeline
- `chi_profiles.py` - profile generation
- `claim_jurisdiction.py` - WHAT/HOW/WHY sentence classifier
- `wrap_article.py` - article template wrapper
- `extract_math.py` - math/equation extraction
- `wordnet_cluster.py` / `wordnet_deep.py` - semantic clustering
- `foldertagger.py` - folder-level metadata
- Sidecar format: `.chi` and `.fmeta` extensions
- Sample sidecars in `filetagger\sample\`

### 2. Corpus Engine
**From:** `D:\DONT TOUCH BOOT UP\chi_qi_v5_statistical_audit_package\corpus_engine_complete\corpus_engine\`
- `run.py` - main runner (scan/organize/learn commands)
- `core/folder_scanner.py` - directory walker
- `core/classifier.py` - domain classifier
- `core/clusterer.py` - similarity clustering
- `core/namer.py` - canonical name generator
- `core/paired_assets.py` - finds related files
- `core/preference_store.py` - learns from corrections
- `consumers/excel_preview.py` - Excel for human review
- `consumers/organizer.py` - reads approved Excel, moves files
- `corpus-consolidation-SKILL.md` - skill doc

### 3. FIS Architecture Spec
**From:** `D:\DONT TOUCH BOOT UP\PICS\Opus 4.8\`
- `FIS.txt` - 2039-line architecture document (the bible)
- `folder_symptom_registry.xlsx` - symptom detection rules
- `files-workbench.html` - UI mockup
- `fis-intelligent.html` / `fis-walkthrough.html` - walkthroughs
- `FIS_FOLDER_INDEX.fisnote` - folder metadata format

### 4. FIS Core (if exists)
**Check:** `D:\DONT TOUCH BOOT UP\FIS\`
- `chi_classifier.py` - imported by filetagger_chi_v2
- Any other core modules

### 5. Doc Profiler (just built tonight)
**From:** `D:\GitHub\faiththruphysics-site\work\doc_profiler.py`
- Raw numerical metrics (A-H layers)
- No LLM dependency, pure Python

---

## UNIFIED ARCHITECTURE

### Pipeline: 10-Step Spine
```
1. SNAPSHOT  - hash every file, record state
2. SCAN      - walk directories, read metadata
3. CLASSIFY  - chi factors, domains, laws, content type
4. PROTECT   - mark roles (canonical, fragile, anomaly)
5. PROPOSE   - suggest renames, moves, dedup
6. PREVIEW   - generate Excel for human review
7. APPROVE   - human edits Excel
8. EXECUTE   - apply approved operations
9. RECORD    - log everything to SQLite
10. LEARN    - extract corrections to preference engine
```

### Folder Structure
```
D:\GitHub\theophysics-fis\
  core\
    scanner.py        - directory walker + file reader
    classifier.py     - chi + domain + law + content type
    clusterer.py      - similarity/duplicate detection
    namer.py          - canonical name generation
    profiler.py       - numerical doc metrics (from doc_profiler.py)
    protector.py      - role assignment (canonical/fragile/anomaly)
  consumers\
    excel_preview.py  - generate review Excel
    organizer.py      - execute approved moves/renames
    sqlite_cache.py   - SQLite read/write layer
  engines\
    preference.py     - learns naming patterns from corrections
    api_fallback.py   - calls DeepSeek/Claude for deep classification
    chi_vectors.py    - chi_qi_v5 vocabulary and scoring
  sidecars\
    folder.py         - .fmeta folder-level metadata
    file.py           - .chi file-level metadata
  run.py              - CLI entry point
  config.py           - all configuration
  CONSOLIDATION_SPEC.md
  archive\            - old/duplicate versions (don't delete)
```

### File Roles (from FIS spec)
Every file gets a ROLE tag in the SQLite cache:
- `canonical` - load-bearing, DO NOT rename/move/break
- `fragile` - has dependencies (code imports, linked assets)
- `anomaly` - unexpected content, needs human review
- `duplicate` - exact hash match with another file
- `near_duplicate` - similar content, different version
- `orphan` - no references point to it
- `archive` - old version, safe to move to archive folder
- `unknown` - couldn't classify, quarantine

### Metadata Extensions
- `.fmeta` - folder-level metadata (JSON, markdown-friendly)
- `.chi` - file-level chi profile (JSON)
Both are gitignored, scannable, and cached in SQLite.

### SQLite Schema
```sql
CREATE TABLE files (
  id INTEGER PRIMARY KEY,
  path TEXT UNIQUE,
  hash_sha256 TEXT,
  size_bytes INTEGER,
  modified_at TEXT,
  scanned_at TEXT,
  role TEXT DEFAULT 'unknown',
  chi_vector TEXT,       -- JSON: {G:0.3, M:0.1, ...}
  domain TEXT,           -- physics/theology/epistemology/...
  law_refs TEXT,         -- JSON: [1,4,7]
  content_type TEXT,     -- paper/code/data/config/media
  cluster_id INTEGER,
  proposed_name TEXT,
  approved INTEGER DEFAULT 0
);
CREATE TABLE folders (
  id INTEGER PRIMARY KEY,
  path TEXT UNIQUE,
  file_count INTEGER,
  symptom TEXT,          -- extension_swamp/duplicate_cluster/etc
  chi_dominant TEXT,
  scanned_at TEXT
);
CREATE TABLE operations_log (
  id INTEGER PRIMARY KEY,
  timestamp TEXT,
  operation TEXT,        -- rename/move/copy/archive/protect
  source TEXT,
  destination TEXT,
  approved_by TEXT,
  executed INTEGER DEFAULT 0
);
CREATE TABLE preferences (
  id INTEGER PRIMARY KEY,
  pattern TEXT,
  correction TEXT,
  engine TEXT,           -- which preference engine suggested it
  confidence REAL,
  learned_at TEXT
);
```

### API Fallback
When local classification confidence is below threshold (0.6):
1. Extract first 2000 chars of file
2. Call DeepSeek (cheapest) with classification prompt
3. Cache result in SQLite so it never calls twice for same file
4. Log the API call cost

### Preference Engines
The naming/classification system should support multiple engines:
1. `rule_based` - regex patterns, extension maps
2. `frequency` - most common patterns in the corpus
3. `chi_vector` - classify by chi factor similarity
4. `api_llm` - DeepSeek/Claude for ambiguous cases

Each engine proposes a name/classification. The Excel preview
shows ALL proposals side by side. Human picks the best one.
The preference store records which engine won, building a
track record over time.

---

## EXECUTION ORDER

1. Create `D:\GitHub\theophysics-fis\` folder structure
2. Copy scripts from all source locations into correct subfolders
3. Put old/duplicate versions in `archive\`
4. Refactor imports to use the new structure
5. Test: `python run.py scan --roots "D:\GitHub\faiththruphysics-site-data" --types .html .md`
6. Test: `python run.py scan --roots "O:\_Theophysics_v4" --types .md .txt`
7. Verify Excel preview generates correctly
8. Verify SQLite schema creates and populates

---

## 6. FIS New Modules (Built June 27, 2026 — This Session)
**From:** `D:\DONT TOUCH BOOT UP\FIS\`

These files were built this session and add capabilities that do NOT exist in
Filetagger Suite or Corpus Engine. They are the "live layer" on top of the
819k-row chi_catalog_v2.db that already exists in filetagger\.

| File | Size | What it does |
|------|------|--------------|
| `fis_classifier.py` | 31KB | 5-tag classifier: domain, chi_factor, law, content_type, evidence |
| `fis_daemon.py` | 41KB | Watchdog daemon covering ALL drive roots, notifications, auto-approve |
| `fis_folder_daemon.py` | 24KB | Separate folder-level daemon |
| `fis_namer.py` | 18KB | Canonical name proposer with compressed code abbreviations |
| `fis_preference_engine.py` | 9.5KB | River LogisticRegression online ML — learns from every decision |
| `fis_enricher.py` | 9.9KB | TF-IDF enricher for low-confidence files |
| `fis_config.json` | 781B | Config: auto-discover drives, skip_exts, notify thresholds |
| `FIS_NAMING_SPEC.md` | 9.5KB | Full naming spec with all abbreviation codes |
| `INSTALL_STARTUP.bat` | 2KB | Registers both daemons with Windows Task Scheduler |
| `fis_catalog.db` | 0B | **EMPTY — daemon has never run. Use chi_catalog_v2.db instead.** |

---

## WHAT FIS HAS THAT THE OTHER SYSTEMS DON'T

### 1. River Online ML Preference Engine (`fis_preference_engine.py`)
- **Corpus Engine** has a `preference_store.py` but it is rule-based / frequency-based.
  FIS uses **River 0.25.0 LogisticRegression with SGD** — it updates the model on
  every single approve/reject with no retraining, no restart.
- Blends raw classifier confidence (60%) with learned preference (40%).
- Forces back to queue if a naming pattern is repeatedly rejected (pref < 0.25).
- Persists to `fis_pref_model.pkl`, logs decisions to `fis_pref_log.jsonl` (replayable).
- **Minimum 10 samples before the engine activates** — uses raw thresholds until then.
- **Consolidation note:** Replace corpus_engine's preference_store.py with this engine.

### 2. Non-Negotiable All-Drives Watchdog (`fis_daemon.py`)
- Filetagger daemon watches only configured folders.
- FIS daemon spins **one Observer per drive root** — covers every drive that exists.
- Config `auto_discover_drives: true` + `skip_drives: ["C:\\"]`.
- On every file CREATE/MOVE/DELETE event anywhere on the system: classify, write .chi sidecar.
- **Consolidation note:** Replace filetagger_daemon.py with this daemon.

### 3. Windows Toast Notifications for Approval Queue (`fis_daemon.py`)
- When pending approvals exceed threshold (default 100), fires a Windows toast via PowerShell.
- Snooze escalation: after `notify_snooze_max` (default 3) ignores, interval drops to 10 min.
- No extra libraries — pure subprocess to `powershell.exe -WindowStyle Hidden`.
- Neither Filetagger nor Corpus Engine has any notification system.

### 4. Low-Confidence TF-IDF Enricher (`fis_enricher.py`)
- When classifier confidence < 50%, instead of blind-queueing, FIS looks up
  similar already-approved files in the DB using TF-IDF (char n-gram).
- Three outcomes: **ENRICHED** (tags replaced from corpus), **COMPARE** (suggestions + context),
  **UNCERTAIN** (manual review).
- Vocabulary comes from filenames, not content — works on any file type.
- **Consolidation note:** Wire `wordnet_expander.py` from filetagger\ into this as a
  second enrichment pass (WordNet synonym expansion on the query terms before TF-IDF).

### 5. Compressed Abbreviation Naming Scheme (`fis_namer.py`, `FIS_NAMING_SPEC.md`)
File schema: `DOMAIN__CT__tag1-tag2[-tag3]__YYYYMMDD__ST.ext`

```
DOMAIN codes:  TH (Theology), DT (Data), CD (Code), PH (Physics),
               CS (Consciousness), EP (Epistemology), MT (Math),
               MR (Media), IF (Info), MD (Medical), TR (Trial),
               LG (Legal), KG (Knowledge), EV (Evidence), AI (AI), GN (General)

Content type:  COD (Code), DOC (Document), DAT (Data), NOT (Notes),
               CFG (Config), PRF (Profile), PAP (Paper), SRM (Sermon),
               IMG (Image), VID (Video), AUD (Audio), BIN (Binary)

Status codes:  AC (Active), DR (Draft), FN (Final), AR (Archive),
               RV (Review), WP (Work-in-Progress)
```

Folder schema: `{class}_{topic-slug}` where class comes from 20 symptom signals
(S01-S08 structural, C01-C08 content, T01-T04 temporal).

Corpus Engine's namer.py generates verbose names. FIS generates scannable
machine-parseable names — every field is a known code, grep-able, sortable.

### 6. Five Non-Negotiable Tags (not 3)
Filetagger tracks: domain, chi_factor, law.
FIS adds: **content_type** (4th) and **evidence** (5th — evidence/fruit scoring).
Evidence scoring detects legal/political/confrontational content in files.

### 7. .chi Sidecar + .fisnote Folder Manifest (NEW FORMAT)
Both open as Markdown. Both have YAML frontmatter with `approved: null` field.
Setting `approved: true/false` in-file triggers the preference engine.
- `.chi` — placed next to each file
- `.fisnote` — placed inside each folder (min 2 files to get one)
Neither the Corpus Engine nor Filetagger uses this inline-approval format.
The filetagger uses `.fmeta` but it is write-only (not wired to learning).

---

## CRITICAL GAPS — FIX BEFORE CONSOLIDATION RUNS

### GAP 1: Wrong Database (BLOCKING)
`fis_catalog.db` is 0 bytes. The daemon has never run.
`chi_catalog_v2.db` in `filetagger\` has **819,008** already-classified rows.
- **Fix:** Update `fis_config.json` `db_path` to point at chi_catalog_v2.db.
- Also bridge the schema: chi_catalog_v2 uses `chi_primary/chi_secondary/chi_vector`
  column names; fis_daemon writes `chi_factor/chi_confidence/content_type/evidence`.
  Need an ALTER TABLE or a migration before first run.

### GAP 2: WordNet Not Wired (HIGH)
`wordnet_expander.py` in `filetagger\` does exactly what fis_enricher should use
for the low-confidence lookup — expand the query terms via WordNet synonyms,
hypernyms, hyponyms before TF-IDF matching. Currently fis_enricher does raw
filename word matching only.
- **Fix:** In `fis_enricher._name_to_text()`, pass words through
  `wordnet_expander.expand_term_list(words, max_total=20)` before vectorizing.

### GAP 3: Symptom Detection Not Implemented (MEDIUM)
`folder_symptom_registry.xlsx` defines 20 folder symptoms used to assign folder
class. All 20 are currently `implemented: No` in fis_folder_daemon.py.
Folder naming (e.g. `S03_name-swamp`) is blocked until these fire.
- **Fix:** Implement the 20 detect_* functions in fis_folder_daemon.py using the
  xlsx rules. File is at `D:\DONT TOUCH BOOT UP\PICS\Opus 4.8\folder_symptom_registry.xlsx`.

### GAP 4: Excel Approval Queue Not Built (MEDIUM)
The spec calls for an Excel preview for human review (Step 6 in the 10-step spine).
`approval_queue.csv` schema is defined in FIS_NAMING_SPEC.md but the exporter
that reads `proposed_name IS NOT NULL AND approved IS NULL` from the DB and writes
to Excel with openpyxl hasn't been written yet.
- **Fix:** Build `consumers/excel_preview.py` using the corpus_engine version as
  a template, adapting columns to the FIS naming schema fields.

### GAP 5: INSTALL_STARTUP.bat Not Run (LOW)
`INSTALL_STARTUP.bat` exists but has not been executed. Neither daemon is registered
with Windows Task Scheduler. Files are not being tagged live.
- **Fix:** Run `INSTALL_STARTUP.bat` as administrator once.

---

## DATABASE INVENTORY

| DB | Location | Rows | Schema |
|----|----------|------|--------|
| `chi_catalog_v2.db` | filetagger\ | **819,008** | chi_primary, chi_secondary, chi_vector, chi_confidence, domain_primary, domain_scores, law_primary, law_scores, content_type, evidence, fruit, anti_fruit |
| `catalog.db` | filetagger\ | 319,777 | path, name, ext, size, md5, created, modified, accessed, tags, category, tier, mtime, scanned |
| `fis_catalog.db` | FIS\ | **0** | files, folders tables defined; never populated |
| `clipsync-db` | Cloudflare D1 | 9,310 items | items table (type, content, tags_json, starred, folder) |

**USE chi_catalog_v2.db as the canonical source. Redirect fis_daemon to it.**

---

## WHAT NOT TO DO
- Do NOT delete any original files. Copy, don't move.
- Do NOT rename files during consolidation. Just organize scripts.
- Do NOT merge filetagger_chi_v2 with corpus_engine blindly.
  They have different architectures. Unify the INTERFACE, keep
  the engines separate internally.
- Do NOT skip the Excel preview step. Human-in-the-loop is sacred.
